# -*- coding:utf-8 -*-
from __future__ import division

import base64
import glob
import os
import tkinter as tk
from tkinter import messagebox
from tkinter.filedialog import askdirectory

import numpy as np
from PIL import Image, ImageTk
from icon import img
from change_realsense_event_piexl import CoordinateConverter


def drawCircle(self, x, y, r, **kwargs):
    return self.create_oval(x - r, y - r, x + r, y + r, width=0, **kwargs)
def drawLine(self,kpts):
    color_list = ["red"] * 7 + ["GreenYellow"] * 7
    skelenton = [[0, 1], [1, 3], [3, 5], [1, 7], [1, 2], [7, 9], [9, 11],
                 [0, 2], [2, 4], [4, 6], [2, 8], [7, 8], [8, 10], [10, 12]]
    for index, sk in enumerate(skelenton):
        pos1 = (int(kpts[sk[0]][0]), int(kpts[sk[0]][1]))
        pos2 = (int(kpts[sk[1]][0]), int(kpts[sk[1]][1]))
        self.create_line(pos1[0],pos1[1],pos2[0],pos2[1],fill=color_list[index])

class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title("Keypoint Annotation Tool")
        # self.parent.geometry("1000x500")
        self.frame = tk.Frame(self.parent)
        self.frame.pack(fill=tk.BOTH, expand=1)
        self.parent.resizable(width=tk.TRUE, height=tk.TRUE)
        self.Covter = CoordinateConverter()
        # 图片大小

        self.img_w_up = 848
        self.img_h_up = 480
        self.img_w_ri = 1280-848
        self.img_h_ri = 480
        self.img_w_down = 1280
        self.img_h_down = 400
        self.COLORS = ['red', 'Lime', 'Blue', 'Yellow', 'Magenta', 'Cyan', 'Maroon',
                       'Navy', 'Olive', 'Purple', 'Teal', '#660066', '#99CCFF',
                       'Cornsilk', 'GreenYellow', '#6B8E23']

        # initialize global state
        self.imageDir = ''  # 图片所在文件夹
        self.eventDir = ""
        self.imageList = []
        self.eventList = []

        self.outDir = ''  # 输出文件夹

        self.cur_color = 0
        self.cur_event = 0
        self.start_event = 0
        self.total = 0
        self.imagename = ''
        self.labelfilename = ''
        self.tkimg = None
        self.eventimage = None

        # reference to bbox
        self.pointIdList = []
        self.pointId = None
        self.point_color_list = []
        self.point_event_list = []
        self.point_event_show = []
        self.root_dir = None
        # ----------------- GUI 部件 ---------------------
        # dir entry & load
        self.btn1 = tk.Button(self.frame, text="选择图片目录",
                           command=self.get_event_dir)
        self.btn1.grid(row=0, column=2, sticky=tk.W + tk.N + tk.S + tk.E)

        self.ldBtn = tk.Button(self.frame, text="开始加载", command=self.loadDir)
        self.ldBtn.grid(row=1, column=2, columnspan=1, sticky=tk.W + tk.N + tk.S + tk.E)
        self.color_event_label = tk.Label(self.frame, text=self.imagename)
        self.color_event_label.grid(row=2, column=2, columnspan=1, sticky=tk.W + tk.N + tk.S + tk.E)
        # main panel for labeling
        self.mainPanel = tk.Canvas(self.frame, bg='lightgray')

        # 鼠标左键点击
        self.mainPanel.bind("<Motion>",self.on_event)
        self.mainPanel.bind("<Leave>",self.no_event)
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        # 快捷键
        self.parent.bind("s", self.saveAll)
        self.parent.bind("a", self.prevImage)  # press 'a' to go backforward
        self.parent.bind("d", self.nextImage)  # press 'd' to go forward
        self.parent.bind("z", self.backword)
        self.parent.bind("w",self.drow_line)
        self.mainPanel.grid(row=0, column=0, rowspan=6, sticky=tk.W + tk.N + tk.S + tk.E)

        # detial_show
        self.detialPanel = tk.Canvas(self.frame, bg="lightgray")
        self.detialPanel.grid(row=0, column=1, rowspan=6, sticky=tk.W + tk.N + tk.S + tk.E)

        # rgb_image_show
        self.eventPanel = tk.Canvas(self.frame, bg="lightgray")
        self.eventPanel.grid(row=6, column=0,columnspan=2, rowspan=7, sticky=tk.W + tk.N + tk.S + tk.E)


        # showing bbox info & delete bbox
        self.lb1 = tk.Label(self.frame, text='关键点坐标:')
        self.lb1.grid(row=3, column=2, columnspan=2, sticky=tk.S + tk.N + tk.W)

        self.listbox = tk.Listbox(self.frame)  # , width=30, height=15)
        self.listbox.grid(row=4, column=2, rowspan=7, columnspan=2, sticky=tk.N + tk.S + tk.E + tk.W)

        self.btnDel = tk.Button(self.frame, text='删除', command=self.delBBox)
        self.btnDel.grid(row=11, column=2, columnspan=2, sticky=tk.S + tk.E + tk.W)
        self.btnClear = tk.Button(
            self.frame, text='清空', command=self.clearBBox)
        self.btnClear.grid(row=12, column=2, columnspan=2, sticky=tk.N + tk.E + tk.W)

        # control panel for image navigation
        self.ctrPanel = tk.Frame(self.frame)
        self.ctrPanel.grid(row=13, column=0, columnspan=3, sticky=tk.E + tk.W + tk.S)
        self.prevBtn = tk.Button(self.ctrPanel, text='<< Prev',
                              width=10, command=self.prevImage)
        self.prevBtn.pack(side=tk.LEFT, padx=5, pady=3)
        self.nextBtn = tk.Button(self.ctrPanel, text='Next >>',
                              width=10, command=self.nextImage)
        self.nextBtn.pack(side=tk.LEFT, padx=5, pady=3)
        self.progLabel = tk.Label(self.ctrPanel, text="Progress:     /    ")
        self.progLabel.pack(side=tk.LEFT, padx=5)
        '''self.tmpLabel = Label(self.ctrPanel, text="Go to Image No.")
        self.tmpLabel.pack(side=LEFT, padx=5)
        self.idxEntry = Entry(self.ctrPanel, width=5)
        self.idxEntry.pack(side=LEFT)'''
        '''self.goBtn = Button(self.ctrPanel, text='Go', command=self.gotoImage)
        self.goBtn.pack(side=LEFT)'''
        self.up_aline_pre = tk.Button(self.ctrPanel, text='color_pred', command=self.color_pred)
        self.up_aline_pre.pack(side=tk.LEFT)
        self.up_aline_next = tk.Button(self.ctrPanel, text='color_next', command=self.color_next)
        self.up_aline_next.pack(side=tk.LEFT)
        self.dowm_aline_pre = tk.Button(self.ctrPanel, text='event_pred', command=self.event_pred)
        self.dowm_aline_pre.pack(side=tk.LEFT)
        self.dowm_aline_next = tk.Button(self.ctrPanel, text='event_next', command=self.event_next)
        self.dowm_aline_next.pack(side=tk.LEFT)
        # display mouse position
        self.disp = tk.Label(self.ctrPanel, text='')
        self.disp.pack(side=tk.RIGHT)

        self.frame.columnconfigure(0, weight=30)
        self.frame.columnconfigure(1, weight=1)
        # self.frame.rowconfigure(6, weight=1)

        # menu
        self.menubar = tk.Menu(self.parent)
        self.helpmenu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='帮助', menu=self.helpmenu)

        self.helpmenu.add_command(label='标注顺序', command=self.key_order)
        self.helpmenu.add_command(label='使用说明', command=self.usage)
        self.helpmenu.add_command(label='关于软件', command=self.about)

        # for debugging
        # self.loadDir()
        self.parent.config(menu=self.menubar)

    def key_order(self):
        messagebox.showinfo(
            title="标注顺序",message="0：头（中部），1：右肩（中部），2：左肩（中部），3：右手肘（中部），4：左手肘（中部），5：右手（中部），6：左手（中部），7：右臀（中部），8：左臀（中部），9：右腿膝盖（中部），10：左腿膝盖（中部），11：右脚（脚踝中部），12：左脚（脚踝中部）"
                                 "\n\n\n 具体可看项目文件夹annt/kepoint_order.png"
        )

    def usage(self):
        messagebox.showinfo(
            title='使用说明', message="0.快捷键：A：上一张图片，S：保存当前结果，D：下一张图片,Z：删除最后一个节点（撤销）\n1. 选择图片所在路径\n2. 点击开始加载\n3. 点击上方画布关节点开始标注，标注是注意关节点及帧是否对应。"
                                  "\n4.如果发现帧不对应可点击下方（color_next/pred,event_next/pred)进行帧间对齐。"
                                  "\n5.如果发现图像最左边最右边及四个角有偏差，属于误差范围，适当调整上方点击位置，尽可能对齐下方关节点。最大偏差0.5cm最左和最右！"
                                  "\n6.当前关节点标注错误，可点右侧关节点坐标显示列表并选中，然后点击删除即可，如果是之前的某个关节点错误，则需要从后往前删除所有当前帧关节点或者直接点击清空，重新标注。"
                                  "\n7.一定要严格按照关节点的顺序进行标注！！！！"
                                  "开始时待下方图片关节点全部出现才开始标注，结束时如存在关节点超出图像则停止标注")

    def about(self):
        messagebox.showinfo(title='关于软件',
                            message="作者:none")
    def get_event_dir(self):
        print("123")
        self.root_dir = askdirectory()
        print("456")
        self.eventDir = os.path.join(self.root_dir, "image_event_binary")
        self.imageDir = os.path.join(self.root_dir, "color")
        self.out_color_Dir = os.path.join(self.root_dir, "label_color")
        self.out_event_Dir = os.path.join(self.root_dir, "label_event")
        self.depthDir = os.path.join(self.root_dir, "depth_raw")
        if not os.path.exists(self.out_color_Dir):
            os.makedirs(self.out_color_Dir)
        if not os.path.exists(self.out_event_Dir):
            os.makedirs(self.out_event_Dir)

    def loadDir(self):

        if self.root_dir == None:
            messagebox.showwarning(
                title='警告', message="请选择文件路径！！！")
            return
        self.imageList = glob.glob(os.path.join(self.imageDir, '*.[jp][pn]g'))
        self.eventList = glob.glob(os.path.join(self.eventDir, '*.[jp][pn]g'))
        self.depthList = glob.glob(os.path.join(self.depthDir, '*.npy'))
        if len(self.imageList) == 0:
            print('No .jpg images found in the specified dir!')
            messagebox.showwarning(
                title='警告', message="对应图片文件夹中没有jpg或png结尾的图片")
            return
        else:
            print("num=%d" % (len(self.imageList)))

        # default to the 1st image in the collection
        self.cur_color = 1
        self.cur_event = 1
        self.total_color = len(self.imageList)
        self.total_event = len(self.eventList)

        self.loadImage()
        print('%d images loaded from %s' % (self.total, self.imageDir))

    def loadImage(self):
        # load image
        imagepath = self.imageList[self.cur_color - 1]

        pil_image = Image.open(imagepath)
        depthpath = self.depthList[self.cur_color - 1]
        self.depth_ary = np.load(depthpath)
        eventpath = self.eventList[self.cur_event - 1]
        pil_event = Image.open(eventpath)

        # get the size of the image
        # 获取图像的原始大小
        global w0, h0
        w0, h0 = pil_image.size

        # 缩放到指定大小
        pil_image = pil_image.resize(
            (self.img_w_up, self.img_h_up), Image.ANTIALIAS)
        pil_event = pil_event.resize(
            (self.img_w_down, self.img_h_down), Image.ANTIALIAS)
        # pil_image = imgresize(w, h, w_box, h_box, pil_image)
        self.img = pil_image
        self.event = pil_event

        self.tkimg = ImageTk.PhotoImage(pil_image)
        self.eventimage = ImageTk.PhotoImage(pil_event)

        self.mainPanel.config(width=self.img_w_up, height=self.img_h_up)
        self.eventPanel.config(width=self.img_w_down, height=self.img_h_down)
        # (width=max(self.tkimg.width(), self.img_w),
        #                       height=max(self.tkimg.height(), self.img_h))
        self.mainPanel.create_image(
            self.img_w_up // 2, self.img_h_up // 2, image=self.tkimg, anchor=tk.CENTER)
        self.eventPanel.create_image(
            self.img_w_down // 2, self.img_h_down // 2, image=self.eventimage, anchor=tk.CENTER
        )

        self.progLabel.config(text="%04d/%04d" % (self.cur_color, self.total_color))
        # load labels
        self.clear()
        self.imagename = os.path.split(imagepath)[-1][:-4]
        self.eventname = os.path.split(eventpath)[-1][:-4]
        str_ = "color——" + self.imagename + "\n" + "event——" + self.eventname
        self.color_event_label["text"] = str_
        labelname_color = self.imagename + '.txt'
        labelname_event = self.eventname + '.txt'
        self.labelfilename_color = os.path.join(self.out_color_Dir, labelname_color)
        self.labelfilename_event = os.path.join(self.out_event_Dir, labelname_event)
        self.show_pre_image()
        bbox_cnt = 0

    def show_pre_image(self):
        if os.path.exists(self.labelfilename_color):
            with open(self.labelfilename_color) as f:
                for (i, line) in enumerate(f):
                    if i == 0:
                        bbox_cnt = int(line.strip())
                        continue
                    tmp = [(t.strip()) for t in line.split()]
                    # print("*********loadimage***********")
                    # print("tmp[0,1]===%.2f, %.2f" %(float(tmp[0]), float(tmp[1])))
                    x1 = float(tmp[0]) * self.img_w_up
                    y1 = float(tmp[1]) * self.img_h_up

                    # 类似鼠标事件
                    self.point_color_list.append((tmp[0], tmp[1]))
                    self.pointIdList.append(self.pointId)
                    self.pointId = None
                    self.listbox.insert(
                        tk.END, '%d:(%s, %s)' % (len(self.pointIdList), tmp[0], tmp[1]))
                    self.listbox.itemconfig(
                        len(self.pointIdList) - 1, fg=self.COLORS[(len(self.pointIdList) - 1) % len(self.COLORS)])
                    drawCircle(self.mainPanel, x1, y1, 3, fill=self.COLORS[(len(self.pointIdList) - 1) % len(self.COLORS)])

                    x_event, y_event = self.Covter.convert(int(float(tmp[0]) * 848), int(float(tmp[1]) * 480), self.depth_ary)
                    self.point_event_list.append((x_event,y_event))
                    self.point_event_show.append([int((x_event / 1280) * self.img_w_down), int((y_event / 800) * self.img_h_down)])
                    drawCircle(self.eventPanel, int((x_event / 1280) * self.img_w_down),
                               int((y_event / 800) * self.img_h_down), 3,
                               fill=self.COLORS[(len(self.pointIdList) - 1) % len(self.COLORS)])
    def updata_image(self):
        self.mainPanel.create_image(
            self.img_w_up // 2, self.img_h_up // 2, image=self.tkimg, anchor=tk.CENTER)
        self.eventPanel.create_image(
            self.img_w_down // 2, self.img_h_down // 2, image=self.eventimage, anchor=tk.CENTER
        )

        self.listbox.delete(0,len(self.pointIdList))
        for index,(x,y) in enumerate(self.point_color_list):

            x1 = float(x) * self.img_w_up
            y1 = float(y) * self.img_h_up
            self.listbox.insert(tk.END, '%d:(%s, %s)' % (index+1, x, y))
            self.listbox.itemconfig(index, fg=self.COLORS[index % len(self.COLORS)])
            drawCircle(self.mainPanel, x1, y1, 3, fill=self.COLORS[index % len(self.COLORS)])
            x_event, y_event = self.Covter.convert(int(float(x) * 848), int(float(y) * 480), self.depth_ary)
            drawCircle(self.eventPanel, int((x_event / 1280) * self.img_w_down),
                       int((y_event / 800) * self.img_h_down), 3,
                       fill=self.COLORS[index % len(self.COLORS)])
    def saveImage(self):
        # print "-----1--self.pointList---------"
        print("Save File Length: %d" % len(self.point_color_list))
        # print "-----2--self.pointList---------"

        if self.labelfilename_event == '' or self.labelfilename_color == "":
            print("labelfilename is empty")
            return

        with open(self.labelfilename_color, 'w') as f:
            f.write('%d\n' % len(self.point_color_list))
            for point in self.point_color_list:
                f.write(' '.join(map(str, point)) + '\n')
        print('Image No. %d saved' % (self.cur_color))
        with open(self.labelfilename_event, 'w') as f:
            f.write('%d\n' % len(self.point_event_list))
            for point in self.point_event_list:
                f.write(' '.join(map(str, point)) + '\n')
        print('Image No. %d saved' % (self.cur_event))

    def saveAll(self, event=None):
        with open(self.labelfilename_color, 'w') as f:
            f.write('%d\n' % len(self.point_color_list))
            for point in self.point_color_list:
                f.write(' '.join(map(str, point)) + '\n')
        print('Image No. %d saved' % (self.cur_color))
        with open(self.labelfilename_event, 'w') as f:
            f.write('%d\n' % len(self.point_event_list))
            for point in self.point_event_list:
                f.write(' '.join(map(str, point)) + '\n')
        print('Image No. %d saved' % (self.cur_event))

    def mouseClick(self, event):
        x1, y1 = event.x, event.y
        x1 = x1 / self.img_w_up
        y1 = y1 / self.img_h_up
        self.point_color_list.append((x1, y1))
        self.pointIdList.append(self.pointId)
        self.pointId = None

        self.listbox.insert(tk.END, '%d:(%.2f, %.2f)' %
                            (len(self.pointIdList), x1, y1))

        print(len(self.point_event_list), self.COLORS[(len(self.pointIdList) - 1) % len(self.COLORS)])
        self.listbox.itemconfig(len(self.pointIdList) - 1, fg=self.COLORS[(len(self.pointIdList) - 1) % len(self.COLORS)])
        drawCircle(self.mainPanel, x1 * self.img_w_up, y1 * self.img_h_up, 3,
                   fill=self.COLORS[(len(self.pointIdList) - 1) % len(self.COLORS)])
        x_event, y_event = self.Covter.convert(int(x1 * 848), int(y1 * 480), self.depth_ary)
        self.point_event_list.append((x_event,y_event))
        self.point_event_show.append([int((x_event / 1280) * self.img_w_down), int((y_event / 800) * self.img_h_down)])
        drawCircle(self.eventPanel, int((x_event / 1280) * self.img_w_down), int((y_event / 800) * self.img_h_down), 3,
                   fill=self.COLORS[(len(self.pointIdList) - 1) % len(self.COLORS)])

    def on_event(self,moved):
        x,y = moved.x,moved.y
        img_array = np.array(self.img)
        img_array[y,:] = (0,0,255)
        img_array[:,x] = (0,0,255)
        on_img = Image.fromarray(img_array[y - 50: y + 50, x - 50: x + 50])
        on_img = on_img.resize((self.img_w_ri, self.img_h_ri), Image.ANTIALIAS)
        self.on_img = ImageTk.PhotoImage(on_img)
        self.detialPanel.config(width=self.img_w_ri, height=self.img_h_ri)
        self.detialPanel.create_image(self.img_w_ri//2, self.img_h_ri//2, image=self.on_img, anchor=tk.CENTER)
    def no_event(self,enter):
        pass
    def drow_line(self,event):
        drawLine(self.eventPanel, self.point_event_show)
    def delBBox(self):
        sel = self.listbox.curselection()
        print(sel)
        if len(sel) != 1:
            return
        idx = int(sel[0])
        self.mainPanel.delete(self.pointIdList[idx])
        self.pointIdList.pop(idx)
        self.point_color_list.pop(idx)
        self.point_event_list.pop(idx)
        self.point_event_show.pop(idx)
        self.listbox.delete(idx)
        self.updata_image()


    def backword(self,event):
        if len(self.pointIdList) < 1:
            return
        self.mainPanel.delete((self.pointIdList[-1]))
        self.pointIdList.pop(-1)
        self.point_color_list.pop(-1)
        self.point_event_list.pop(-1)
        self.point_event_show.pop(-1)
        self.listbox.delete(-1)
        self.updata_image()

    def clearBBox(self):
        for idx in range(len(self.pointIdList)):
            self.mainPanel.delete(self.pointIdList[idx])
        self.listbox.delete(0, len(self.point_color_list))
        self.pointIdList = []
        self.point_color_list = []
        self.point_event_list = []
        self.point_event_show = []
        self.updata_image()


    def clear(self):
        for idx in range(len(self.pointIdList)):
            self.mainPanel.delete(self.pointIdList[idx])
        self.listbox.delete(0, len(self.point_color_list))
        self.pointIdList = []
        self.point_color_list = []
        self.point_event_list = []
        self.point_event_show = []

    def prevImage(self, event=None):
        self.saveImage()
        if self.cur_color > 1 and self.cur_event > 2:
            self.cur_color -= 1
            self.cur_event -= 2
            self.loadImage()
        else:
            messagebox.showwarning(title='警告', message="已是第一页！！！")

    def nextImage(self, event=None):
        self.saveImage()
        if self.cur_color < self.total_color and self.cur_event < self.total_event:
            self.cur_color += 1
            self.cur_event += 2
            self.loadImage()
        else:
            messagebox.showwarning(title='警告', message="已是最后一页！！！")
    '''def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.saveImage()
            self.cur_color = idx
            self.cur_event = idx * 2 + self.start_event
            self.loadImage()'''
    def color_pred(self):
        if self.cur_color > 1:
            self.cur_color -= 1
            self.loadImage()
        else:
            messagebox.showwarning(title='警告', message="已是第一页！！！")
    def color_next(self):
        if self.cur_color < self.total_color:
            self.cur_color += 1
            self.loadImage()
        else:
            messagebox.showwarning(title='警告', message="已是最后一页！！！")
    def event_pred(self):
        if self.cur_event > 1:
            self.cur_event -= 1
            self.loadImage()
        else:
            messagebox.showwarning(title='警告', message="已是第一页！！！")
    def event_next(self):
        if self.cur_event < self.total_event:
            self.cur_event += 1
            self.start_event += 1
            self.loadImage()
        else:
            messagebox.showwarning(title='警告', message="已是最后一页！！！")
    def imgresize(self, w, h, w_box, h_box, pil_image):
        '''
        resize a pil_image object so it will fit into
        a box of size w_box times h_box, but retain aspect ratio
        '''
        f1 = 1.0 * w_box / w  # 1.0 forces float division in Python2
        f2 = 1.0 * h_box / h
        factor = min([f1, f2])
        # use best down-sizing filter
        width = int(w * factor)
        height = int(h * factor)
        return pil_image.resize((width, height), Image.ANTIALIAS)


if __name__ == '__main__':
    root = tk.Tk()
    tmp = open("eye.ico", "wb+")
    tmp.write(base64.b64decode(img))
    tmp.close()
    root.iconbitmap("eye.ico")
    os.remove("eye.ico")

    tool = LabelTool(root)
    root.mainloop()
