import imageio
import numpy as np
from os.path import join as oj
import os, cv2, math
import matplotlib.pyplot as plt
import logging, sys
from scipy import misc
from skimage.feature import match_template

import beak
import meniscus
import tongue


# check if bird is drinking
def bird_is_drinking(tube_big_motion):
    motion_thresh = 0
    if np.sum(tube_big_motion > 0) > motion_thresh * tube_big_motion.shape[0] * tube_big_motion.shape[1]:
        return True
    else:
        return False


def track_clip(fname, tube_pos, tube_capacity,
               out_dir="out", NUM_FRAMES=None, NUM_LINES=20, save_ims=False):
    # open video and create background subtractors
    logging.info('tracking %s', fname)
    cap = cv2.VideoCapture(fname)
    fgbg = cv2.createBackgroundSubtractorMOG2()
    fgbg_tube = cv2.createBackgroundSubtractorMOG2()
    fgbg_tube_big = cv2.createBackgroundSubtractorMOG2()

    # initialize loop
    frame_num = 0
    if NUM_FRAMES is None:
        NUM_FRAMES = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    logging.info('num_frames %d', NUM_FRAMES)

    # make out_dir
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    # tube dimensions
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    top, left, bot = tube_pos
    tube_height = bot - top
    top_big = max(top - tube_height, 0)  # bounded by 0
    bot_big = min(bot + tube_height, height - 1)  # bounded by bottom of frame
    left_big = max(0, left - (width - left) * 2)  # bounded by 0

    # stats to track
    stats = {}
    points_to_track = ["is_drinking", "beak_tip", "tongue_tip"]
    for point in points_to_track:
        stats[point] = np.zeros((NUM_FRAMES, 1))
    bars, barsx = [], []

    # loop over frames
    ret, frame = cap.read()
    while ret and frame_num < NUM_FRAMES:
        if frame_num % 100 == 0:
            logging.info('frame_num %d', frame_num)

        # big tube for drinking
        tube_big = frame[top_big:bot_big, left_big:left]
        tube_big_motion = fgbg_tube_big.apply(tube_big)
        bird_drinking = bird_is_drinking(tube_big_motion)
        stats["is_drinking"][frame_num] = bird_drinking
        if bird_drinking:

            # beak
            # stats["beak_tip"][frame_num] = x_beak
            # x_beak = beak.beak_from_frame_motion(tube_big, x_beak)

            # tube for measuring
            tube = frame[top:bot, left:]
            tube_motion = fgbg_tube.apply(tube)
            denoising_param = 100
            tube_motion = cv2.fastNlMeansDenoising(tube_motion, denoising_param, denoising_param,
                                                   templateWindowSize=7, searchWindowSize=21)

            # track meniscus
            bars.append(meniscus.simple_meniscus(tube_motion)[0])
            barsx.append(meniscus.simple_meniscus(tube_motion)[1])

            # track tongue tip
            # x_tongue = tongue.tongue_from_tube_motion(tube_motion, x_meniscus, x_tongue)
            # stats["tongue_tip"][frame_num] = x_tongue

            # save
            if save_ims and frame_num % 2 == 0:
                # colorize
                frame_motion = fgbg.apply(frame)
                frame_motion_rgb = cv2.cvtColor(frame_motion, cv2.COLOR_GRAY2RGB)
                tube_big_motion_rgb = cv2.cvtColor(tube_big_motion, cv2.COLOR_GRAY2RGB)
                tube_motion_rgb = cv2.cvtColor(tube_motion, cv2.COLOR_GRAY2RGB)  # just for drawing

                # draw things
                cv2.circle(frame, center=(left, top), radius=6, color=(255, 0, 0), thickness=5)
                cv2.circle(frame, center=(left, bot), radius=6, color=(255, 0, 0), thickness=5)
                # cv2.circle(tube_motion_rgb, center=(int(x_meniscus), int(10)),
                #            radius=15, color=(255, 0, 0), thickness=5)

                # imageio.imwrite(oj(out_dir, 'frame_' + str(frame_num) + '.jpg'), frame_motion_rgb)
                # imageio.imwrite(oj(out_dir, 'orig_frame_' + str(frame_num) + '.jpg'), frame)
                imageio.imwrite(oj(out_dir, 'tube_' + str(frame_num) + '.jpg'), tube)
                imageio.imwrite(oj(out_dir, 'tube_motion_' + str(frame_num) + '.jpg'), tube_motion_rgb)
                # imageio.imwrite(oj(out_dir, 'tube_big_' + str(frame_num) + '.jpg'), tube_big)
                # imageio.imwrite(oj(out_dir, 'tube_big_motion_' + str(frame_num) + '.jpg'), tube_big_motion_rgb)

        # read next frame
        frame_num += 1
        ret, frame = cap.read()

        # scaling
    #    meniscus_arr *= tube_capacity * ... # todo: this needs to be fixed

    # saving
    for point in stats:
        plt.figure(figsize=(14, 6))
        plt.plot(range(NUM_FRAMES), stats[point], 'o')
        plt.xlabel('Frame number')
        plt.ylabel(point)
        plt.savefig(oj(out_dir, point + '.png'))
        np.savetxt(oj(out_dir, point + '.csv'), stats[point], fmt="%3.2f", delimiter=',')
    bars = np.array(bars)
    print(bars.shape)
    np.savetxt(oj(out_dir, 'bars' + '.csv'), bars, fmt="%3.2f", delimiter=',')

    barsx = np.array(barsx).transpose()
    print(barsx.shape)
    np.savetxt(oj(out_dir, 'barsx' + '.csv'), barsx, fmt="%3.2f", delimiter=',')

    # release video
    cap.release()
    cv2.destroyAllWindows()
    print('succesfully completed')


if __name__ == "__main__":
    # hyperparams - denoising_param, conf_thresh, jump_thresh
    logging.basicConfig(stream=sys.stdout, level=logging.INFO, format='%(message)s')
    data_folder = '/Users/chandan/drive/research/vision/hummingbird/data'
    # tube_pos_a = (110, 1230, 260)  # (top, left, bot)
    tube_pos_b = (84, 485, 126)
    tube_capacity = 300  # in mL
    fname = oj(data_folder, 'side', 'b.mov')
    out_dir = "out_a"
    track_clip(fname, tube_pos_b, tube_capacity,
               out_dir=out_dir, NUM_FRAMES=None, save_ims=True)