import os
import subprocess
import open3d as o3d
import cv2
import customtkinter as ctk
from tkinter import *
from PIL import Image, ImageTk
import numpy as np
import pyrealsense2 as rs
import serial
from data_processing import draw_calculated_volume
from image_viewer import ImageViewer
from serial_rtk import create_rtk_thread, get_rtk_data
from datetime import datetime

WINDOW_WIDTH = 1900 #1320
WINDOW_HEIGHT = 1000 #900
TAB_TITLE_MAIN = "저장소 목록"
TAB_TITLE_RECORD = '촬영'
TAB_TITLE_IMAGE_VIEWER = "저장영상 보기"
TAB_TITLE_CONVERTING = "3D 변환"
TAB_TITLE_3D_VIEWER = "3D 재생"
TAB_TITLE_REPORT = "Tkinter"
CAMERA_STATE_PREVIEW = 'PREVIEW'
CAMERA_STATE_RECORDING = 'RECORDING'
CAMERA_STATE_RECORDING_PAUSED = 'RECORDING_PAUSED'
CAMERA_STATE_STOPPED = 'STOPPED'

class MainTabView(ctk.CTkTabview):
    def __init__(self, master, **kwargs):
        super().__init__(master)

        self.root = master

        self.init_menu()

        self.image_label = ctk.CTkLabel(master)
        self.selected_tab = None
        self.camera_state = CAMERA_STATE_STOPPED
        self.save_status = False
        self.frame_counts = 0
        self.pipeline = None
        self.align = None
        self.rtk_thread = None
        self.open3d_process = None

        self.create_gps_state_frame()
        self.create_tabs()

    def create_gps_state_frame(self):
        # create gps state frame and add gps_state_label, gps_x_label, gps_y_label
        self.gps_state_frame = Frame(master=self.root)
        # 0: No connection, 1: GPS SPS, 2: D-GPS, 3: GPS PPS, 4: RTK Fixed, 5: RTK Floating, 6: Dead Reckoning
        self.gps_time = ctk.CTkLabel(master=self.gps_state_frame, text="2024-01-01 12:00:00", width=20, font=("Century Gothic", 20))
        self.gps_state_label = ctk.CTkLabel(master=self.gps_state_frame, text="RTK Fixed", width=20, font=("Century Gothic", 20))
        self.gps_x_label = ctk.CTkLabel(master=self.gps_state_frame, text="Latitude:", width=20, font=("Century Gothic", 20))
        self.gps_x_val_label = ctk.CTkLabel(master=self.gps_state_frame, text="127.12345678", width=20, font=("Century Gothic", 20))
        self.gps_y_label = ctk.CTkLabel(master=self.gps_state_frame, text="Longitude:", width=20, font=("Century Gothic",20))
        self.gps_y_val_label = ctk.CTkLabel(master=self.gps_state_frame, text="38.12345678", width=20, font=("Century Gothic", 20))
        self.gps_a_label = ctk.CTkLabel(master=self.gps_state_frame, text="Altitude:", width=20, font=("Century Gothic", 20))
        self.gps_a_val_label = ctk.CTkLabel(master=self.gps_state_frame, text="29.910", width=20, font=("Century Gothic", 20))

        # Add the labels to the frame
        self.gps_time.grid(row=0, column=0, padx=5, pady=5)
        self.gps_state_label.grid(row=0, column=1, padx=5, pady=5)
        self.gps_x_label.grid(row=0, column=2,  padx=5, pady=5)
        self.gps_x_val_label.grid(row=0, column=3,  padx=5, pady=5)
        self.gps_y_label.grid(row=0, column=4, padx=5, pady=5)
        self.gps_y_val_label.grid(row=0, column=5, padx=5, pady=5)
        self.gps_a_label.grid(row=0, column=6, padx=5, pady=5)
        self.gps_a_val_label.grid(row=0, column=7, padx=5, pady=5)

        # hide gps_time
        self.gps_time.grid_remove()

        # Add the frame to the root window
        self.gps_state_frame.grid(row=0, column=0, padx=5, pady=5, sticky='ew')

        # start rtk thread and update gps state
        port = 'COM9'
        self.rtk_thread = create_rtk_thread(port, self.update_gps_state)
        if self.rtk_thread is not None:
            self.rtk_thread.start()
        else:
            print("Failed to create RTK thread")

    def update_gps_state(self, rtk_status):
        # print("update_gps_state", rtk_status)
        if rtk_status is None:
            return
        
        # if rtk_status has Timestamp update gps_time
        if 'Timestamp' in rtk_status:
            # convert timestamp '081003.607' to a datetime object
            timestamp = str(rtk_status['Timestamp'])
            if timestamp != '0.0': 
                dt = datetime.strptime(timestamp, "%H%M%S.%f")
                # Replace the year, month, and day with the current year, month, and day
                now = datetime.now()
                dt = dt.replace(year=now.year, month=now.month, day=now.day)
                # Format the datetime object as a string
                formatted_dt = dt.strftime("%Y-%m-%d %H:%M:%S")
                self.gps_time.configure(text=formatted_dt)
        # if rtk_status has GPS Quality Indicator update gps_state_label
        if 'GPS Quality Indicator' in rtk_status:
            # 0: No connection, 1: GPS SPS, 2: D-GPS, 3: GPS PPS, 4: RTK Fixed, 5: RTK Floating, 6: Dead Reckoning
            gps_status = rtk_status['GPS Quality Indicator']
            gps_status_text = 'No connection' if gps_status == '0' else 'GPS SPS' if gps_status == '1' else 'D-GPS' if gps_status == '2' else 'GPS PPS' if gps_status == '3' else 'RTK Fixed' if gps_status == '4' else 'RTK Floating' if gps_status == '5' else 'Dead Reckoning' if gps_status == '6' else 'Unknown'
            self.gps_state_label.configure(text=gps_status_text)
        # if rtk_status has Latitude update gps_x_val_label
        if 'Latitude' in rtk_status:
            self.gps_x_val_label.configure(text=rtk_status['Latitude'])
        # if rtk_status has Longitude update gps_y_val_label
        if 'Longitude' in rtk_status:
            self.gps_y_val_label.configure(text=rtk_status['Longitude'])
        # if rtk_status has Antenna Alt above sea level (mean) update gps_a_val_label
        if 'Antenna Alt above sea level (mean)' in rtk_status:
            self.gps_a_val_label.configure(text=rtk_status['Antenna Alt above sea level (mean)'])

    # Main menu
    def init_menu(self):
        menus = Menu(self.root)
        self.root.config(menu = menus)

        file_menu = Menu(menus)
        menus.add_cascade(label = "File", menu = file_menu)
        file_menu.add_command(label = "Exit", command = self.root.destroy)

        help_menu = Menu(menus)
        menus.add_cascade(label = "Help", menu = help_menu)
        help_menu.add_command(label = "About", command = self.show_about)

    def show_about(self):
        about_window = Toplevel(self.root)
        about_window.title("About")
        about_window.geometry("300x200")
        about_window.resizable(False, False)
        about_window.transient(self.root)
        about_window.grab_set()
        # contents: title, version, author, contact, description
        about_contents = {
            "title": "tkinter app",
            "version": "1.0.0",
            "author": "sungyong",
            "description": "tkinter test app",
            "created": "2024-01-30"
        }
        about_contents_str = f'버전: {about_contents["version"]}\n{about_contents["author"]}\n{about_contents["description"]}\n{about_contents["created"]}'
        about_text = ctk.CTkTextbox(about_window)
        about_text.pack(fill="both", expand=True)
        about_text.insert('end', about_contents_str)
        about_text.configure(font=("Century Gothic", 20))

    def get_selected_tab(self):
        # Update the selected_tab variable
        self.selected_tab = self.tab_view.get()
        # print("selected_tab", self.selected_tab)
        return self.selected_tab

    def log(self, msg):
        self.log_textbox.insert('end', msg + '\n')
        self.log_textbox.see('end')
        # if over 1000 lines, delete first line
        if self.log_textbox.index('end-1c') == '1000.0':
            self.log_textbox.delete('1.0', '2.0')

    def create_tabs(self):
        # Create the tab control
        # CTkTabview creates a tabview, similar to a notebook in tkinter. 
        # The tabs, which are created with .add("<tab-name>") are CTkFrames 
        # and can be used like CTkFrames. Any widgets can be placed on them

        self.tab_view = ctk.CTkTabview(self.root, width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
        self.tab_main = ctk.CTkFrame(self.tab_view)
        self.tab_record = ctk.CTkFrame(self.tab_view)
        self.tab_image_viewer = ctk.CTkFrame(self.tab_view)
        self.tab_mesh_convert = ctk.CTkFrame(self.tab_view)
        self.tab_report = ctk.CTkFrame(self.tab_view, fg_color="transparent")

        # Add the tabs to the tab control
        self.tab_main = self.tab_view.add(TAB_TITLE_MAIN)
        self.tab_record = self.tab_view.add(TAB_TITLE_RECORD)
        self.tab_image_viewer = self.tab_view.add(TAB_TITLE_IMAGE_VIEWER)
        self.tab_report = self.tab_view.add(TAB_TITLE_REPORT)     
        for button in self.tab_view._segmented_button._buttons_dict.values():
            button.configure(width=100, height=40, font=("Century Gothic", 20)) #Change font using font object

        # row0: gps state
        # row1: tab frame
        # col0: gps state, col1: gps x, col2: gps y
        self.tab_view.grid(row=1, column=0, padx=2, pady=2, columnspan=3, rowspan=2)  # Use grid with row and column

        self.init_frame_main()
        self.init_frame_record()
        self.init_frame_image_viewer()
        self.load_saved_folder()
        
    def init_frame_record(self):
        preview_icon = PhotoImage(file='assets/icon-play.png')
        start_record_icon = PhotoImage(file='assets/icon-record.png')
        pause_record_icon = PhotoImage(file='assets/icon-pause.png')
        stop_record_icon = PhotoImage(file='assets/icon-stop.png')

        self.preview_button = ctk.CTkButton(self.tab_record, text="미리보기", font=("Century Gothic", 20), image=preview_icon, command=self.preview)
        self.preview_button.grid(row=0, column=0, padx=5, pady=5, sticky='ew')

        self.start_record_button = ctk.CTkButton(self.tab_record, text="녹화 시작", font=("Century Gothic", 20), image=start_record_icon, command=self.start_record)
        self.start_record_button.grid(row=0, column=1, padx=5, pady=5, sticky='ew')

        self.pause_record_button = ctk.CTkButton(self.tab_record, text="일시정지", font=("Century Gothic", 20), image=pause_record_icon, command=self.pause_record)
        self.pause_record_button.grid(row=0, column=2, padx=5, pady=5, sticky='ew')

        self.stop_record_button = ctk.CTkButton(self.tab_record, text="녹화 완료", font=("Century Gothic", 20), image=stop_record_icon,  command=self.stop_record)
        self.stop_record_button.grid(row=0, column=3, padx=5, pady=5, sticky='ew')

        # Bind the <FocusIn> event to the tab_record widget
        self.tab_record.bind('<FocusIn>', self.preview)


    def init_frame_image_viewer(self, selected_folder=None):
        self.image_viewer = ImageViewer(self.tab_image_viewer, selected_folder)
        # set image_viewer size to fit tab_image_viewer
        self.image_viewer.config(width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
        self.image_viewer.grid(row=0, column=0)


    def load_saved_folder(self):
        folder_list = os.listdir("datasets")
        # filter only folder
        folder_list = [folder for folder in folder_list if os.path.isdir(os.path.join("datasets", folder))]
        self.log('load_saved_folder: %s' % str(folder_list))

        # display folder list to selectable list widget
        self.listbox = Listbox(self.tab_main)
        # set default bigger font size
        self.listbox.config(font=("Courier", 15), width=40, height=10)
        self.listbox.grid(row=1, column=0, columnspan=2, rowspan=5, padx=5, pady=5, sticky='NW')
        for folder in folder_list:
            self.listbox.insert(0, folder)

        # Bind the onselect method to the <<ListboxSelect>> event
        self.listbox.bind('<<ListboxSelect>>', self.on_dataset_select)
        self.toggle_buttons('disabled')


    def init_frame_main(self):
        # row0: col0: explorer, col1: load_saved_folder(r1,c0 ~ r3,c1)
        # row1: col0: image_view, col2:other buttons
        # row2,3: col2: other buttons
        # c3: log textarea
        ###############################
        # r0,c0 | r0,c1 | r0,c2 | r0,c3
        # r1,c0 | r1,c1 | r1,c2 | r1,c3
        # r2,c0 | r2,c1 | r2,c2 | r2,c3
        # r3,c0 | r3,c1 | r3,c2 | r3,c3
        # r4,c0 | r4,c1 | r4,c2 | r4,c3
        ###############################
        explorer_icon = PhotoImage(file='assets/icon-explorer.png')
        load_saved_folder_icon = PhotoImage(file='assets/icon-file.png')

        converting_3d_icon = PhotoImage(file='assets/icon-3d.png')
        image_view_icon = PhotoImage(file='assets/icon-image.png')
        ply_viewer_icon = PhotoImage(file='assets/icon-ply.png')
        report_icon = PhotoImage(file='assets/icon-report.png')

        # create text box
        # set width from window with - 4 column width
        self.log_textbox = ctk.CTkTextbox(self.tab_main, width=650, height=10, font=("Century Gothic", 14))

        self.explorer_button = ctk.CTkButton(
            self.tab_main, text="저장소 열기", font=("Century Gothic", 14), command=lambda: os.system("explorer.exe %s" % os.path.realpath("datasets")),
            image=explorer_icon
        )
        self.load_saved_folder_button = ctk.CTkButton(
            self.tab_main, text="목록 다시 읽기", font=("Century Gothic", 14), command=self.load_saved_folder,
            image=load_saved_folder_icon
        )
        self.converting_3d_button = ctk.CTkButton(
            self.tab_main, text="3D 변환",font=("Century Gothic", 14),  command=lambda: self.converting_3d(self.selected_folder_name),
            image=converting_3d_icon
        )
        self.image_view_button = ctk.CTkButton(
            self.tab_main, text="저장영상 보기", font=("Century Gothic", 14), command=lambda: self.go_tab_image_viewer(self.selected_folder_name),
            image=image_view_icon
        )
        self.ply_viewer_button = ctk.CTkButton(
            self.tab_main, text="PLY 보기", font=("Century Gothic", 14), command=lambda: self.ply_viewer(self.selected_folder_name),
            image=ply_viewer_icon
        )
        self.report_button = ctk.CTkButton(
            self.tab_main, text="Tkiner", font=("Century Gothic", 14), command=lambda: self.go_tab_report(self.selected_folder_name),
            image=report_icon
        )
        self.upload_button = ctk.CTkButton(
            self.tab_main, text="서버업로드", font=("Century Gothic", 14), command=lambda: self.upload_to_server(self.selected_folder_name),
            image=image_view_icon
        )
                
        self.explorer_button.grid(row=0, column=0, padx=5, pady=5)
        self.load_saved_folder_button.grid(row=0, column=1, padx=5, pady=5)

        self.converting_3d_button.grid(row=1, column=2, padx=5, pady=5)
        self.image_view_button.grid(row=2, column=2, padx=5, pady=5)
        self.ply_viewer_button.grid(row=3, column=2, padx=5, pady=5)
        self.report_button.grid(row=4, column=2, padx=5, pady=5)
        self.upload_button.grid(row=5, column=2, padx=5, pady=5)
        self.log_textbox.grid(row=1, column=3, rowspan=5, padx=5, pady=5, sticky='NSWE')

        self.toggle_buttons('disabled')


    def upload_to_server(self, selected_folder):
        self.log("upload_to_server: " + selected_folder + "...")
        # update ui
        self.refresh_ui()
        res = upload_folder(selected_folder, logger=self.log)
        self.log("upload_to_server: " + res)
        self.refresh_ui()

    def refresh_ui(self):
        self.root.update_idletasks()
        self.root.update()

    def converting_3d(self, selected_folder):
        self.log("converting_3d: " + selected_folder + "...")
        # update ui
        self.refresh_ui()
        convert_3d(selected_folder, logger=self.log)
        self.refresh_ui()
        self.log('체적 계산 중...')
        generate_report(selected_folder, logger=self.log)
        self.refresh_ui()
        self.log("converting_3d: " + selected_folder + " 완료")

    def go_tab_image_viewer(self, selected_folder):
        self.log("go_tab_image_viewer")
        self.tab_view.set("저장영상 보기")
        self.image_viewer.set_folder(selected_folder)
        self.image_viewer.grid(row=0, column=0)

    def go_tab_report(self, selected_folder):
        self.log("go_tab_report")

        # check volume_result.json exists in selected_folder
        if not os.path.exists('datasets/' + selected_folder + '/volume_result.json'):
            self.log("체적 계산이 완료되지 않았습니다.")
            return
        
        self.tab_view.set("Tkiner")
        draw_calculated_volume(self.tab_report, selected_folder)
        
    def ply_viewer(self, selected_folder):
        file_path = 'datasets/' + selected_folder + '/integrated.ply'
        self.log("ply_viewer: " + file_path)
        self.mesh_viewer(file_path)

    def set_camera_buttons(self, state):
        if state == CAMERA_STATE_PREVIEW:
            self.preview_button.configure(state="disabled")
            self.start_record_button.configure(state="enabled", text="녹화 시작")
            self.pause_record_button.configure(state="enabled")
            self.stop_record_button.configure(state="enabled")
        elif state == CAMERA_STATE_STOPPED:
            self.preview_button.configure(state="enabled")
            self.start_record_button.configure(state="enabled", text="녹화 시작")
            self.pause_record_button.configure(state="disabled")
            self.stop_record_button.configure(state="disabled")
        elif state == CAMERA_STATE_RECORDING:
            self.preview_button.configure(state="disabled")
            self.start_record_button.configure(state="disabled", text="녹화중...")
            self.pause_record_button.configure(state="enabled")
            self.stop_record_button.configure(state="enabled")
        elif state == CAMERA_STATE_RECORDING_PAUSED:
            self.preview_button.configure(state="disabled")
            self.start_record_button.configure(state="enabled", text="녹화 시작")
            self.pause_record_button.configure(state="disabled")
            self.stop_record_button.configure(state="enabled")
        else:
            self.preview_button.configure(state="disabled")
            self.start_record_button.configure(state="disabled", text="녹화 시작")
            self.pause_record_button.configure(state="disabled")
            self.stop_record_button.configure(state="disabled")
        self.refresh_ui()

    def start_record(self):
        print("start_record")
        self.save_status = True
        # set disable button to prevent double click
        self.set_camera_buttons(CAMERA_STATE_RECORDING)

    def pause_record(self):
        print("pause_record")
        print("Recording color + depth image %06d" % self.frame_counts)
        self.save_status = False
        self.set_camera_buttons(CAMERA_STATE_RECORDING_PAUSED)

    def stop_record(self):
        self.save_status = False
        print("Saved color + depth image %06d" % self.frame_counts)
        self.frame_counts = 0
        self.set_camera_buttons(CAMERA_STATE_STOPPED)
        self.stop_preview()

    def preview(self):
        if self.get_selected_tab() != TAB_TITLE_RECORD:
            return
        if self.camera_state == CAMERA_STATE_PREVIEW:
            return

        self.set_camera_buttons(CAMERA_STATE_PREVIEW)
        self.preview_thread()

    def stop_preview(self):
        self.camera_state = CAMERA_STATE_STOPPED
        self.log("stop_preview")
        self.set_camera_buttons(CAMERA_STATE_STOPPED)

    def preview_thread(self, event=None):
        self.log("preview thread")

        self.camera_state = CAMERA_STATE_PREVIEW
        self.pipeline, self.align = setupPipeline("nHD") # nHD, HD, FHD

        colorizer = rs.colorizer()
        try:
            # loop while the preview tab is selected
            while self.get_selected_tab() == '촬영' and self.camera_state == CAMERA_STATE_PREVIEW:
                frames = self.pipeline.wait_for_frames()

                aligned_frames = self.align.process(frames)
                color_frame = aligned_frames.get_color_frame()
                depth_frame = aligned_frames.get_depth_frame()

                if not depth_frame or not color_frame:
                    continue

                depth_image = np.asanyarray(depth_frame.get_data())
                depth_color_frame = colorizer.colorize(depth_frame)

                # Convert frames to numpy arrays to render image in opencv
                depth_color_image = np.asanyarray(depth_color_frame.get_data())

                color_image = np.asanyarray(color_frame.get_data())

                preview_depth_color_image = cv2.resize(depth_color_image, (640, 360))
                preview_color_image = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
                preview_color_image = cv2.resize(preview_color_image, (640, 360))

                depth_image_pil = Image.fromarray(preview_depth_color_image)
                color_image_pil = Image.fromarray(preview_color_image)

                depth_image_tk = ImageTk.PhotoImage(depth_image_pil)
                color_image_tk = ImageTk.PhotoImage(color_image_pil)

                if not hasattr(self, 'color_preview_label'):
                    self.color_preview_label = ctk.CTkLabel(self.tab_record, image=color_image_tk, text="Color", fg_color=("#DB3E39", "#821D1A"), text_color="#821D1A")
                    self.color_preview_label.image = color_image_tk
                    self.color_preview_label.grid(row=1, column=0, columnspan=2, pady=5)  # Use grid with row and column
                if not hasattr(self, 'depth_preview_label'):
                    self.depth_preview_label = ctk.CTkLabel(self.tab_record, image=depth_image_tk, text="Depth", fg_color=("#DB3E39", "#821D1A"), text_color="#DB3E39")
                    self.depth_preview_label.image = depth_image_tk
                    self.depth_preview_label.grid(row=1, column=2, columnspan=2, pady=5)  # Use grid with row and column
                # If the preview labels already exist, update them
                else:
                    self.depth_preview_label.configure(image=depth_image_tk)
                    self.depth_preview_label.image = depth_image_tk
                    self.color_preview_label.configure(image=color_image_tk)
                    self.color_preview_label.image = color_image_tk


                if self.save_status:
                    if self.frame_counts == 0:
                        path_output, path_color, path_depth = createOutputDirectory("datasets/")
                        save_intrinsic_as_json(join(path_output, "camera_intrinsic.json"), color_frame)
                        save_reconstruction_config_as_yml(path_output)

                    cv2.imwrite("%s/%06d.png" % (path_depth, self.frame_counts), depth_image)
                    cv2.imwrite("%s/%06d.jpg" % (path_color, self.frame_counts), color_image)
                    self.frame_counts += 1
                    if self.frame_counts == 1000:
                        print("최대 촬영 매수에 도달했습니다.")
                        self.save_status = False
                        self.stop_record()

                self.root.update_idletasks()
                self.root.update()
        except Exception as e:
            print(e)
        finally:
            self.stop_preview()
            self.depth_preview_label.image = None
            self.color_preview_label.image = None


    # display selected folder's color and depth image
    def on_dataset_select(self, evt):
        # get selected folder name
        w = evt.widget
        index = int(w.curselection()[0])
        value = w.get(index)
        self.log('selected item %d: "%s"' % (index, value))
        self.selected_folder_name = value
        self.toggle_buttons('enabled')

    # toggle disable/enable of all buttons
    def toggle_buttons(self, state):
        self.image_view_button.configure(state=state)
        self.ply_viewer_button.configure(state=state)
        self.converting_3d_button.configure(state=state)
        self.report_button.configure(state=state)
        self.upload_button.configure(state=state)

        
    def mesh_viewer(self, ply_file_path):
        # ignore if "open3d" process is exist
        if self.open3d_process:
            return
        self.open3d_process = True
        self.log("mesh_viewer")
        
        # open3d process
        self.open3d_process = subprocess.Popen(["open3d", "draw", ply_file_path])
        self.open3d_process.wait()
        self.open3d_process = None

    # 보고서
    def show_report(self, points):
        
        # Create a blank image
        img = np.zeros((500, 500, 3), dtype=np.uint8)

        # Map 3D points to 2D image coordinates
        img_points = points[:, :2].astype(int)

        # Draw points on the image
        for point in img_points:
            cv2.circle(img, tuple(point), 1, (255, 255, 255), -1)

        # Convert image to RGB format
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # Convert image to PhotoImage format for displaying in Tkinter
        img_tk = ImageTk.PhotoImage(Image.fromarray(img_rgb))

        # Update the image label
        self.image_label.config(image=img_tk)
        self.image_label.image = img_tk
