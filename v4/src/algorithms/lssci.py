import numpy as np
import math as m
from tqdm import tqdm

from robot_system import *
import utils as u


class LocalStateSplitCovarianceIntersection():


    def __init__(self, robot_system, dataset):
        self.robot_system = robot_system
        self.dataset = dataset

        self.dt = self.robot_system.dt
        self.duration = self.robot_system.duration

        self.comm_prob_fail = self.robot_system.comm_prob_fail


    def prediction(self, t):

        dataset = self.dataset

        for r in range(NUM_ROBOTS):

            # get odometry times
            times = [dataset['Robot' + str(r+1)]['Odometry'][k]['Time [s]'] for k in range(len(dataset['Robot' + str(r+1)]['Odometry']))]

            # get nearest index
            idx = np.argmin(np.abs(t - times))

            # extract odometry
            v = dataset['Robot' + str(r+1)]['Odometry'][idx]['forward velocity [m/s]']
            a_v = dataset['Robot' + str(r+1)]['Odometry'][idx]['angular velocity [rad/s]']

            # state prediction
            x = self.robot_system.xys[2*r]
            y = self.robot_system.xys[2*r+1]
            theta = self.robot_system.thetas[r]

            x += m.cos(theta) * v * self.dt
            y += m.sin(theta) * v * self.dt
            theta += a_v * self.dt

            # ground truth orientation (comment this block to use estimated orientation)
            times_gt = [dataset['Robot' + str(r+1)]['Groundtruth'][k]['Time [s]'] for k in range(len(dataset['Robot' + str(r+1)]['Groundtruth']))]
            idx_gt = np.argmin(np.abs(t - times_gt))
            theta = dataset['Robot' + str(r+1)]['Groundtruth'][idx_gt+1]['orientation [rad]']

            self.robot_system.xys[2*r] = x
            self.robot_system.xys[2*r+1] = y
            self.robot_system.thetas[r] = theta

            # covariance prediction
            G = u.rot_mtx(theta)
            W = np.identity(2) * (0.05**2)*(0.09**2) * 10 * self.dt**2
            W[1, 1] = 0
            Q = G @ W @ G.T

            self.robot_system.covs_i[2*r:2*r+2, 2*r:2*r+2] += Q
            # self.robot_system.covs[2*r:2*r+2, 2*r:2*r+2] += Q


    def absolute_observation(self, t):

        dataset = self.dataset

        for r in range(NUM_ROBOTS):

            # get measurement times
            times = [dataset['Robot' + str(r+1)]['Measurement'][k]['Time [s]'] for k in range(len(dataset['Robot' + str(r+1)]['Measurement']))]

            # get nearest indices
            idxs = np.where(np.abs(t - times) == np.abs(t - times).min())[0]

            # check all measurements
            for idx in idxs:

                # check if the observation is a landmark
                barcode_num = dataset['Robot' + str(r+1)]['Measurement'][idx]['Subject #']

                num_landmarks = len(dataset['Landmark_Groundtruth'])
                barcode_nums = [self.robot_system.landmarks[l].barcode_num for l in range(num_landmarks)]

                if barcode_num in barcode_nums:

                    # extract landmark measurements
                    _range = dataset['Robot' + str(r+1)]['Measurement'][idx]['range [m]']
                    bearing = dataset['Robot' + str(r+1)]['Measurement'][idx]['bearing [rad]']

                    # direct measurement
                    z = np.array([_range * m.cos(bearing), _range * m.sin(bearing)])

                    # robot location
                    x = self.robot_system.xys[2*r]
                    y = self.robot_system.xys[2*r+1]
                    theta = self.robot_system.thetas[r]

                    # landmark location
                    l_idx = np.where(np.asarray(barcode_nums) == barcode_num)[0][0]
                    l_x = self.robot_system.landmarks[l_idx].xy[0]
                    l_y = self.robot_system.landmarks[l_idx].xy[1]

                    # predicted measurement
                    dx = l_x - x
                    dy = l_y - y
                    z_hat = u.rot_mtx(theta).T @ np.array((dx, dy))

                    # construct measurement matrix
                    H_i = np.zeros((2,2*NUM_ROBOTS))
                    H_i[0, 2*r] = -1.0
                    H_i[1, 2*r+1] = -1.0
                    H = u.rot_mtx(theta).T @ H_i

                    # absolute observation update
                    V = u.rot_mtx(bearing)
                    meas_var = np.array([[RANGE_VAR, 0.0], [0.0, BEARING_VAR * _range**2]])
                    R = V @ meas_var @ V.T

                    covs_total = self.robot_system.covs_i + self.robot_system.covs_d

                    innovation = H @ covs_total @ H.T + R
                    Kalman_gain = covs_total @ H.T @ np.linalg.inv(innovation)

                    self.robot_system.xys += Kalman_gain @ (z - z_hat)

                    covs_total -= Kalman_gain @ H @ covs_total

                    self.robot_system.covs_i = (np.identity(2*NUM_ROBOTS) - Kalman_gain @ H) \
                        @ self.robot_system.covs_i \
                        @ (np.identity(2*NUM_ROBOTS) - Kalman_gain @ H).T \
                        + Kalman_gain @ R @ Kalman_gain.T

                    self.robot_system.covs_d = covs_total - self.robot_system.covs_i


    # def relative_observation(self, t):

    #     dataset = self.dataset

    #     for r in range(NUM_ROBOTS):

    #         # get measurement times
    #         times = [dataset['Robot' + str(r+1)]['Measurement'][k]['Time [s]'] for k in range(len(dataset['Robot' + str(r+1)]['Measurement']))]

    #         # get nearest indices
    #         idxs = np.where(np.abs(t - times) == np.abs(t - times).min())[0]

    #         # check all measurements
    #         for idx in idxs:

    #             # check if the observation is a robot
    #             barcode_num = dataset['Robot' + str(r+1)]['Measurement'][idx]['Subject #']
    #             barcode_nums = [self.robot_system.robots[rr].barcode_num for rr in range(NUM_ROBOTS)]

    #             # extract robot measurements
    #             if barcode_num in barcode_nums:
    #                 _range = dataset['Robot' + str(r+1)]['Measurement'][idx]['range [m]']
    #                 bearing = dataset['Robot' + str(r+1)]['Measurement'][idx]['bearing [rad]']

    #                 # direct measurement
    #                 z = np.array([_range * m.cos(bearing), _range * m.sin(bearing)])

    #                 # robot location
    #                 x = self.robot_system.xys[2*r]
    #                 y = self.robot_system.xys[2*r+1]
    #                 theta = self.robot_system.thetas[r]

    #                 # observed robot location
    #                 r_j = np.where(np.asarray(barcode_nums) == barcode_num)[0][0]
    #                 x_j = self.robot_system.xys[2*r_j]
    #                 y_j = self.robot_system.xys[2*r_j+1]
    #                 theta_j = self.robot_system.thetas[r_j]

    #                 # construct measurement matrix
    #                 H_ij = np.zeros((2,2*NUM_ROBOTS))
    #                 H_ij[0, 2*r] = -1.0
    #                 H_ij[1, 2*r+1] = -1.0
    #                 H_ij[0, 2*r_j] = 1.0
    #                 H_ij[1, 2*r_j+1] = 1.0

    #                 H = u.rot_mtx(theta).T @ H_ij

    #                 # predicted measurement
    #                 z_hat = H @ self.robot_system.xys

    #                 # relative observation update
    #                 V = u.rot_mtx(bearing)
    #                 meas_var = np.array([[RANGE_VAR, 0.0], [0.0, BEARING_VAR]])
    #                 R = V @ meas_var @ V.T

    #                 e = 0.83

    #                 covs_i = self.robot_system.covs_i.copy()
    #                 covs_d = self.robot_system.covs_d.copy()

    #                 p_2 = 1./(e) * covs_d[2*r_j:2*r_j+2, 2*r_j:2*r_j+2] + covs_i[2*r_j:2*r_j+2, 2*r_j:2*r_j+2]
    #                 p_1 = (1./(1-e)) * covs_d[2*r:2*r+2, 2*r:2*r+2] + covs_i[2*r:2*r+2, 2*r:2*r+2] # 漏加括号

    #                 Kalman_gain = p_2 @ np.linalg.inv(p_1 + p_2)

    #                 hat_j = self.robot_system.xys[2*r:2*r+2] + u.rot_mtx(theta) @ z

    #                 self.robot_system.xys[2*r_j:2*r_j+2] += Kalman_gain @ (hat_j - self.robot_system.xys[2*r_j:2*r_j+2])

    #                 cov_total = (np.identity(2) - Kalman_gain) @ p_2

    #                 self.robot_system.covs_i[2*r_j:2*r_j+2, 2*r_j:2*r_j+2] = (np.identity(2) - Kalman_gain) @ covs_i[2*r_j:2*r_j+2, 2*r_j:2*r_j+2] @ (np.identity(2) - Kalman_gain).T \
    #                                                                             + Kalman_gain @ covs_i[2*r:2*r+2, 2*r:2*r+2] @ Kalman_gain.T

    #                 self.robot_system.covs_d[2*r_j:2*r_j+2, 2*r_j:2*r_j+2] = cov_total - self.robot_system.covs_i[2*r_j:2*r_j+2, 2*r_j:2*r_j+2]

    def relative_observation(self, t):

        dataset = self.dataset

        for r in range(NUM_ROBOTS):

            # get measurement times
            times = [dataset['Robot' + str(r+1)]['Measurement'][k]['Time [s]'] for k in range(len(dataset['Robot' + str(r+1)]['Measurement']))]

            # get nearest indices
            idxs = np.where(np.abs(t - times) == np.abs(t - times).min())[0]

            # check all measurements
            for idx in idxs:

                # check if the observation is a robot
                barcode_num = dataset['Robot' + str(r+1)]['Measurement'][idx]['Subject #']
                barcode_nums = [self.robot_system.robots[rr].barcode_num for rr in range(NUM_ROBOTS)]

                # extract robot measurements
                if barcode_num in barcode_nums:
                    _range = dataset['Robot' + str(r+1)]['Measurement'][idx]['range [m]']
                    bearing = dataset['Robot' + str(r+1)]['Measurement'][idx]['bearing [rad]']
                    # if(abs(bearing)>3): print(bearing)
                    # direct measurement
                    z = np.array([_range * m.cos(bearing), _range * m.sin(bearing)])

                    # robot location
                    x = self.robot_system.xys[2*r]
                    y = self.robot_system.xys[2*r+1]
                    theta = self.robot_system.thetas[r]

                    # observed robot location
                    r_j = np.where(np.asarray(barcode_nums) == barcode_num)[0][0]
                    x_j = self.robot_system.xys[2*r_j]
                    y_j = self.robot_system.xys[2*r_j+1]
                    theta_j = self.robot_system.thetas[r_j]

                    # construct measurement matrix
                    # H_ij = np.zeros((2,2*NUM_ROBOTS))
                    # H_ij[0, 2*r] = -1.0
                    # H_ij[1, 2*r+1] = -1.0
                    # H_ij[0, 2*r_j] = 1.0
                    # H_ij[1, 2*r_j+1] = 1.0

                    # H = u.rot_mtx(theta).T @ H_ij

                    # # predicted measurement
                    # z_hat = H @ self.robot_system.xys

                    # relative observation update
                    V = u.rot_mtx(bearing)
                    meas_var = np.array([[RANGE_VAR, 0.0], [0.0, _range**2 * BEARING_VAR]])
                    R = V @ meas_var @ V.T

                    e = 0.83

                    covs_i = self.robot_system.covs_i.copy()
                    covs_d = self.robot_system.covs_d.copy()

                    p_2 = 1./(e) * covs_d[2*r_j:2*r_j+2, 2*r_j:2*r_j+2] + covs_i[2*r_j:2*r_j+2, 2*r_j:2*r_j+2]
                    sigma_i_i = covs_i[2*r:2*r+2,2*r:2*r+2] + u.rot_mtx(theta) * R * u.rot_mtx(theta).T
                    p_1 = (1./(1-e)) * covs_d[2*r:2*r+2, 2*r:2*r+2] + sigma_i_i # 漏加括号

                    Kalman_gain = p_2 @ np.linalg.inv(p_1 + p_2)
                    if(abs(np.trace(Kalman_gain))>1): continue
                    hat_j = self.robot_system.xys[2*r:2*r+2] + u.rot_mtx(theta) @ z

                    self.robot_system.xys[2*r_j:2*r_j+2] += Kalman_gain @ (hat_j - self.robot_system.xys[2*r_j:2*r_j+2])

                    cov_total = (np.identity(2) - Kalman_gain) @ p_2

                    self.robot_system.covs_i[2*r_j:2*r_j+2, 2*r_j:2*r_j+2] = (np.identity(2) - Kalman_gain) @ covs_i[2*r_j:2*r_j+2, 2*r_j:2*r_j+2] @ (np.identity(2) - Kalman_gain).T \
                                                                                + Kalman_gain @ sigma_i_i @ Kalman_gain.T

                    self.robot_system.covs_d[2*r_j:2*r_j+2, 2*r_j:2*r_j+2] = cov_total - self.robot_system.covs_i[2*r_j:2*r_j+2, 2*r_j:2*r_j+2]
                    # self.robot_system.covs[2*r_j:2*r_j+2, 2*r_j:2*r_j+2] = cov_total.copy()
                    # print([Kalman_gain])
                    # print([np.trace(Kalman_gain), t, r, r_j])
                    # print([x_j, y_j, hat_j[0], hat_j[1], self.robot_system.xys[2*r_j], self.robot_system.xys[2*r_j+1]])

    def save_est(self, t):

        dataset = self.dataset

        for r in range(NUM_ROBOTS):

            # get measurement times
            times = [dataset['Robot' + str(r+1)]['Measurement'][k]['Time [s]'] for k in range(len(dataset['Robot' + str(r+1)]['Measurement']))]

            # get nearest index
            idx = np.argmin(np.abs(t - times))

            # save into history
            time = dataset['Robot' + str(r+1)]['Measurement'][idx]['Time [s]']
            x = self.robot_system.xys[2*r]
            y = self.robot_system.xys[2*r+1]
            theta = self.robot_system.thetas[r]
            cov = self.robot_system.covs_i[2*r:2*r+2, 2*r:2*r+2] + self.robot_system.covs_d[2*r:2*r+2, 2*r:2*r+2]

            self.robot_system.robots[r].history['est'].append({'time': np.copy(time), 'x': np.copy(x), 'y': np.copy(y), 'theta': np.copy(theta), 'cov': np.copy(cov)})


    def save_gt(self, t):

        dataset = self.dataset

        for r in range(NUM_ROBOTS):

            # get ground truth times
            times = [dataset['Robot' + str(r+1)]['Groundtruth'][k]['Time [s]'] for k in range(len(dataset['Robot' + str(r+1)]['Groundtruth']))]

            # get nearest index
            idx = np.argmin(np.abs(t - times))

            # save into history
            time = dataset['Robot' + str(r+1)]['Groundtruth'][idx]['Time [s]']
            x = dataset['Robot' + str(r+1)]['Groundtruth'][idx]['x [m]']
            y = dataset['Robot' + str(r+1)]['Groundtruth'][idx]['y [m]']
            theta = dataset['Robot' + str(r+1)]['Groundtruth'][idx]['orientation [rad]']

            self.robot_system.robots[r].history['gt'].append({'time': np.copy(time), 'x': np.copy(x), 'y': np.copy(y), 'theta': np.copy(theta)})


    def run(self, start_time, end_time):

        # initialize time
        t = start_time

        with tqdm(total=(self.duration/self.dt), leave=False) as pbar:

            while t <= end_time:

                elapsed_time = np.abs(t - start_time)

                # prediction (time propagation) step
                self.prediction(t)

                # absolute observation update (landmarks)
                self.absolute_observation(t)

                comm_success = np.random.uniform()

                if comm_success >= self.comm_prob_fail:

                    # relative observation update (other robots)
                    self.relative_observation(t)

                # save the estimate
                self.save_est(t)

                # save the ground truth
                self.save_gt(t)

                # update the time
                t = t + self.dt
                pbar.update()

