# -*- coding:utf-8 -*-
from __future__ import division

import base64
import glob
import os
import random
import tkinter.messagebox
from tkinter import *
from tkinter import messagebox
from tkinter.filedialog import askdirectory

import numpy as np
from PIL import Image, ImageTk
from icon import img
from change_realsense_event_piexl import CoordinateConverter


def drawCircle(self, x, y, r, **kwargs):
    return self.create_oval(x - r, y - r, x + r, y + r, width=0, **kwargs)


class LabelTool():
    def __init__(self, master):
        # set up the main frame
        self.parent = master
        self.parent.title("Keypoint Annotation Tool")
        # self.parent.geometry("1000x500")
        self.frame = Frame(self.parent)
        self.frame.pack(fill=BOTH, expand=1)
        self.parent.resizable(width=TRUE, height=TRUE)
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

        self.cur = 0
        self.total = 0
        self.imagename = ''
        self.labelfilename = ''
        self.tkimg = None
        self.eventimage = None

        # reference to bbox
        self.pointIdList = []
        self.pointId = None
        self.pointList = []
        self.root_dir = None
        # ----------------- GUI 部件 ---------------------
        # dir entry & load
        self.btn1 = Button(self.frame, text="选择图片目录",
                           command=self.get_event_dir)
        self.btn1.grid(row=0, column=2, sticky=W + N + S + E)

        self.ldBtn = Button(self.frame, text="开始加载", command=self.loadDir)
        self.ldBtn.grid(row=2, column=2, columnspan=1, sticky=W + N + S + E)

        # main panel for labeling
        self.mainPanel = Canvas(self.frame, bg='lightgray')

        # 鼠标左键点击
        self.mainPanel.bind("<Motion>",self.on_event)
        self.mainPanel.bind("<Leave>",self.no_event)
        self.mainPanel.bind("<Button-1>", self.mouseClick)
        # 快捷键
        self.parent.bind("s", self.saveAll)
        self.parent.bind("a", self.prevImage)  # press 'a' to go backforward
        self.parent.bind("d", self.nextImage)  # press 'd' to go forward
        self.mainPanel.grid(row=0, column=0, rowspan=6, sticky=W + N + S + E)

        # detial_show
        self.detialPanel = Canvas(self.frame, bg="lightgray")
        self.detialPanel.grid(row=0, column=1, rowspan=6, sticky=W + N + S + E)

        # rgb_image_show
        self.eventPanel = Canvas(self.frame, bg="lightgray")
        self.eventPanel.grid(row=6, column=0,columnspan=2, rowspan=7, sticky=W + N + S + E)


        # showing bbox info & delete bbox
        self.lb1 = Label(self.frame, text='关键点坐标:')
        self.lb1.grid(row=3, column=2, columnspan=2, sticky=S + N + W)

        self.listbox = Listbox(self.frame)  # , width=30, height=15)
        self.listbox.grid(row=4, column=2, rowspan=7, columnspan=2, sticky=N + S + E + W)

        self.btnDel = Button(self.frame, text='删除', command=self.delBBox)
        self.btnDel.grid(row=11, column=2, columnspan=2, sticky=S + E + W)
        self.btnClear = Button(
            self.frame, text='清空', command=self.clearBBox)
        self.btnClear.grid(row=12, column=2, columnspan=2, sticky=N + E + W)

        # control panel for image navigation
        self.ctrPanel = Frame(self.frame)
        self.ctrPanel.grid(row=13, column=0, columnspan=3, sticky=E + W + S)
        self.prevBtn = Button(self.ctrPanel, text='<< Prev',
                              width=10, command=self.prevImage)
        self.prevBtn.pack(side=LEFT, padx=5, pady=3)
        self.nextBtn = Button(self.ctrPanel, text='Next >>',
                              width=10, command=self.nextImage)
        self.nextBtn.pack(side=LEFT, padx=5, pady=3)
        self.progLabel = Label(self.ctrPanel, text="Progress:     /    ")
        self.progLabel.pack(side=LEFT, padx=5)
        self.tmpLabel = Label(self.ctrPanel, text="Go to Image No.")
        self.tmpLabel.pack(side=LEFT, padx=5)
        self.idxEntry = Entry(self.ctrPanel, width=5)
        self.idxEntry.pack(side=LEFT)
        self.goBtn = Button(self.ctrPanel, text='Go', command=self.gotoImage)
        self.goBtn.pack(side=LEFT)

        # display mouse position
        self.disp = Label(self.ctrPanel, text='')
        self.disp.pack(side=RIGHT)

        self.frame.columnconfigure(0, weight=30)
        self.frame.columnconfigure(1, weight=1)
        # self.frame.rowconfigure(6, weight=1)

        # menu
        self.menubar = Menu(self.parent)
        self.helpmenu = Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label='帮助', menu=self.helpmenu)

        self.helpmenu.add_command(label='使用说明', command=self.usage)
        self.helpmenu.add_command(label='关于软件', command=self.about)

        # for debugging
        # self.loadDir()
        self.parent.config(menu=self.menubar)

    def usage(self):
        messagebox.showinfo(
            title='使用说明', message="1. 选择图片所在路径\n2. 点击开始加载\n3. 点击上方画布关节点开始标注")

    def about(self):
        messagebox.showinfo(title='关于软件',
                            message="作者:none")
    def get_event_dir(self):
        self.root_dir = askdirectory()
        self.eventDir = os.path.join(self.root_dir, "image_event_binary")
        self.imageDir = os.path.join(self.root_dir, "color")
        self.outDir = os.path.join(self.root_dir, "label")
        self.depthDir = os.path.join(self.root_dir, "depth_raw")
        if not os.path.exists(self.outDir):
            os.makedirs(self.outDir)

    def loadDir(self):
        # for debug
        # self.imageDir = "./data/images"
        # self.outDir = "./data/labels"
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
        self.cur = 1
        self.total = len(self.imageList)

        if not os.path.exists(self.outDir):
            os.mkdir(self.outDir)

        self.loadImage()
        print('%d images loaded from %s' % (self.total, self.imageDir))

    def loadImage(self):
        # load image
        imagepath = self.imageList[self.cur - 1]

        pil_image = Image.open(imagepath)
        depthpath = self.depthList[self.cur - 1]
        self.depth_ary = np.load(depthpath)
        eventpath = self.eventList[(self.cur - 1)*2+1]
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
            self.img_w_up // 2, self.img_h_up // 2, image=self.tkimg, anchor=CENTER)
        self.eventPanel.create_image(
            self.img_w_down // 2, self.img_h_down // 2, image=self.eventimage, anchor=CENTER
        )

        self.progLabel.config(text="%04d/%04d" % (self.cur, self.total))
        # load labels
        self.clear()
        self.imagename = os.path.split(imagepath)[-1][:-4]
        labelname = self.imagename + '.txt'
        print(labelname)
        self.labelfilename = os.path.join(self.outDir, labelname)
        self.show_pre_image()
        bbox_cnt = 0

    def show_pre_image(self):
        if os.path.exists(self.labelfilename):
            with open(self.labelfilename) as f:
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
                    self.pointList.append((tmp[0], tmp[1]))
                    self.pointIdList.append(self.pointId)
                    self.pointId = None
                    self.listbox.insert(
                        END, '%d:(%s, %s)' % (len(self.pointIdList), tmp[0], tmp[1]))
                    self.listbox.itemconfig(
                        len(self.pointIdList) - 1, fg=self.COLORS[(len(self.pointIdList) - 1) % len(self.COLORS)])
                    drawCircle(self.mainPanel, x1, y1, 3, fill=self.COLORS[(len(self.pointIdList) - 1) % len(self.COLORS)])

                    x_event, y_event = self.Covter.convert(int(float(tmp[0]) * 848), int(float(tmp[1]) * 480), self.depth_ary)
                    drawCircle(self.eventPanel, int((x_event / 1280) * self.img_w_down),
                               int((y_event / 800) * self.img_h_down), 3,
                               fill=self.COLORS[(len(self.pointIdList) - 1) % len(self.COLORS)])
    def saveImage(self):
        # print "-----1--self.pointList---------"
        print("Save File Length: %d" % len(self.pointList))
        # print "-----2--self.pointList---------"

        if self.labelfilename == '':
            print("labelfilename is empty")
            return

        with open(self.labelfilename, 'w') as f:
            f.write('%d\n' % len(self.pointList))
            for bbox in self.pointList:
                f.write(' '.join(map(str, bbox)) + '\n')
        print('Image No. %d saved' % (self.cur))

    def saveAll(self, event=None):
        with open(self.labelfilename, 'w') as f:
            f.write('%d\n' % len(self.pointList))
            for bbox in self.pointList:
                f.write(' '.join(map(str, bbox)) + '\n')
        print('Image No. %d saved' % (self.cur))

    def mouseClick(self, event):
        x1, y1 = event.x, event.y
        x1 = x1 / self.img_w_up
        y1 = y1 / self.img_h_up
        self.pointList.append((x1, y1))
        self.pointIdList.append(self.pointId)
        self.pointId = None

        self.listbox.insert(END, '%d:(%.2f, %.2f)' %
                            (len(self.pointIdList), x1, y1))

        print(len(self.pointList), self.COLORS[(len(self.pointIdList) - 1) % len(self.COLORS)])
        self.listbox.itemconfig(len(self.pointIdList) - 1, fg=self.COLORS[(len(self.pointIdList) - 1) % len(self.COLORS)])
        drawCircle(self.mainPanel, x1 * self.img_w_up, y1 * self.img_h_up, 3,
                   fill=self.COLORS[(len(self.pointIdList) - 1) % len(self.COLORS)])
        x_event, y_event = self.Covter.convert(int(x1 * 848), int(y1 * 480), self.depth_ary)
        print(x_event,y_event)
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
        self.detialPanel.create_image(self.img_w_ri//2, self.img_h_ri//2, image=self.on_img, anchor=CENTER)
    def no_event(self,enter):
        pass

    def delBBox(self):
        sel = self.listbox.curselection()
        print(sel)
        if len(sel) != 1:
            return
        idx = int(sel[0])
        self.mainPanel.delete(self.pointIdList[idx])
        self.pointIdList.pop(idx)
        self.pointList.pop(idx)
        self.listbox.delete(idx)

        self.saveImage()
        self.loadImage()

    def clearBBox(self):
        for idx in range(len(self.pointIdList)):
            self.mainPanel.delete(self.pointIdList[idx])
        self.listbox.delete(0, len(self.pointList))
        self.pointIdList = []
        self.pointList = []

        self.saveImage()
        self.loadImage()

    def clear(self):
        for idx in range(len(self.pointIdList)):
            self.mainPanel.delete(self.pointIdList[idx])
        self.listbox.delete(0, len(self.pointList))
        self.pointIdList = []
        self.pointList = []

    def prevImage(self, event=None):
        self.saveImage()
        if self.cur > 1:
            self.cur -= 1
            self.loadImage()
        else:
            messagebox.showwarning(title='警告', message="已是第一页！！！")

    def nextImage(self, event=None):
        self.saveImage()
        if self.cur < self.total:
            self.cur += 1
            self.loadImage()
        else:
            messagebox.showwarning(title='警告', message="已是最后一页！！！")
    def gotoImage(self):
        idx = int(self.idxEntry.get())
        if 1 <= idx and idx <= self.total:
            self.saveImage()
            self.cur = idx
            self.loadImage()

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
    root = Tk()
    tmp = open("eye.ico", "wb+")
    tmp.write(base64.b64decode(img))
    tmp.close()
    root.iconbitmap("eye.ico")
    os.remove("eye.ico")

    tool = LabelTool(root)
    root.mainloop()