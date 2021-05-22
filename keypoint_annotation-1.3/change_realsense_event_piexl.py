import json
import os
import numpy as np
import pyrealsense2 as rs

class CoordinateConverter:
    def __init__(self):
        with open("annt\\intrinsics.json") as f:
            intrinsics = json.load(f)
        self.data = None
        self.intrinsics = rs.intrinsics()
        self.intrinsics.width = intrinsics["depth"]["width"]
        self.intrinsics.height = intrinsics["depth"]["height"]
        self.intrinsics.fx = intrinsics["depth"]["fx"]
        self.intrinsics.fy = intrinsics["depth"]["fy"]
        self.intrinsics.ppx = intrinsics["depth"]["ppx"]
        self.intrinsics.ppy = intrinsics["depth"]["ppy"]
        self.intrinsics.coeffs = intrinsics["depth"]["coeffs"]
        self.depth_scale = intrinsics["depth_scale"]

        self.cam_matrix_left = np.load("annt\\m_l.npy")
        self.cam_matrix_right = np.load("annt\\m_r.npy")
        self.R = np.load("annt\\R.npy")
        self.T = np.load("annt\\T.npy")
    def get_m(self):
        r_t = np.hstack([self.R, self.T])
        temp = np.zeros(len(r_t[0]))
        temp[-1] = 1
        r_t = np.vstack([r_t, temp])
        m_l = np.hstack([self.cam_matrix_left, np.array([[0]] * len(self.cam_matrix_left))])
        m_r = np.dot(np.hstack([self.cam_matrix_right, np.array([[0]] * len(self.cam_matrix_right))]), r_t)
        return m_l,m_r
    def convert(self, x: int, y: int,data):
        distance = data[y][x]  # * self.depth_scale
        camera_coordinate = rs.rs2_deproject_pixel_to_point(self.intrinsics, [x, y], distance)
        camera_coordinate = np.array(camera_coordinate).reshape(3,1)
        m_l,m_r = self.get_m()
        s_r = np.dot(m_r[-1], np.vstack([camera_coordinate, [1]]))
        r_pi = np.dot(m_r, np.vstack([camera_coordinate, [1]])) / s_r
        return r_pi[0],r_pi[1]