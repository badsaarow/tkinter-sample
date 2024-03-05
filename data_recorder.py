import os
import time

import argparse
import serial
import pyrealsense2 as rs
import numpy as np
import cv2
from multiprocessing import Process, Queue, Value, freeze_support

def rgbdProcess(args:argparse.Namespace, rtk_ready:Value, exit_signal:Value, gps_queue:Queue):
    '''
    RGBD 영상 촬영을 위한 함수
    '''
    last_gps_data = None    #마지막에 도착한 GPS 데이터를 가리키는 변수

    # 설정된 출력 위치를 기준으로 폴더생성
    path_output, path_color, path_depth = createOutputDirectory(args.output_folder)

    # RGBD 카메라 초기 설정 
    # 기본 HD(1280 X 720)으로 촬영
    pipeline, align = setupPipeline(mode=args.capture_resolution)
    
    # RTK 데이터 저장을 위한 파일 생성
    rtK_file = open(os.path.join(path_output, 'rtk_output.txt'), 'w')
    
    # RTK 장비가 준비되지 않은 경우 대기
    while not rtk_ready.value:
        print('RTK를 대기 중 입니다.')
        time.sleep(1)

    frame_count = 0
    try:
        # 종료 시그널을 전파받을 때까지 실행
        while not exit_signal.value:
            # gps 데이터를 수신한 기록이 있는지 확인
            if not gps_queue.empty():
                last_gps_data = gps_queue.get()

            # RGB 영상과 정렬된 RGB 영상 획득
            frames = pipeline.wait_for_frames()
            aligned_frames = align.process(frames)

            # RGB 영상에 정렬된 depth 영상 획득
            aligned_depth_frame = aligned_frames.get_depth_frame()
            color_frame = aligned_frames.get_color_frame()

            # 영상 획득 결과 검증
            if not aligned_depth_frame or not color_frame:
                continue

            depth_image = np.asanyarray(aligned_depth_frame.get_data())
            color_image = np.asanyarray(color_frame.get_data())

            # 수신한 gps 데이터가 있는 경우에 데이터 기록 시작
            if last_gps_data:
                if frame_count == 0:
                    save_intrinsic_as_json(
                        os.join(path_output, "camera_intrinsic.json"),
                        color_frame)
                    save_reconstruction_config_as_yml(path_output)
                if not args.debug:
                    cv2.imwrite("%s/%06d.png" % \
                            (path_depth, frame_count), depth_image)
                    cv2.imwrite("%s/%06d.jpg" % \
                            (path_color, frame_count), color_image)
                else:
                    print("Saved color + depth image %06d" % frame_count)
                frame_count += 1

                rtK_file.write(last_gps_data.getInfoText())

            # 화면에 RGB 영상과 depth 영상 표시
            renderImage(color_image, depth_image)
            key = cv2.waitKey(1)

            if key == 27:   # ESC 버튼 누를 경우 exit_signal 전파 및 종료
                print("Saved color + depth image %06d" % frame_count)
                cv2.destroyAllWindows()
                exit_signal.value = True

            if frame_count == args.max_capture_size:
                print("최대 촬영 매수에 도달했습니다.")
                print("Saved color + depth image %06d" % frame_count)
                cv2.destroyAllWindows()
                exit_signal.value = True

    finally:
        pipeline.stop()
        rtK_file.close()

def rtkProcess(args:argparse.Namespace, rtk_ready:Value, exit_signal:Value, gps_queue:Queue):
    '''
    RTK 데이터 수신을 위한 함수
    '''

    # 시리얼 통신 초기 설정
    ser = serial.Serial()
    ser.baudrate = 115200
    ser.port = args.port
    ser.bytesize = serial.EIGHTBITS
    ser.stopbits = serial.STOPBITS_ONE
    ser.parity = serial.PARITY_NONE

    # RTK 장비가 준비되지 않은 경우 대기
    while not rtk_ready.value:
        try:
            ser.open()
            rtk_ready.value = True
        except serial.SerialException:
            print('장치가 아직 연결되지 않았습니다.')
            time.sleep(1)

    # 종료 시그널 받을 때까지 데이터 수신 및 저장
    try:
        while not exit_signal.value:
            if ser.in_waiting > 0:
                rcvdata = ser.read(ser.in_waiting)
                if rcvdata[0:4] == b'CAFE' and \
                    rcvdata[60:64] == b'BEBE':
                    # CAFE, BEBE 빠진 데이터
                    gps_data = GPSINFO(rcvdata[4:60])
                    
                    # Queue를 통해 프로세스간 통신
                    gps_queue.put(gps_data)
            time.sleep(0.1)
    finally:
        ser.close()       
