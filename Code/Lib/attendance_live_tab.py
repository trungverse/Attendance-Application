import os
import tkinter
from tkinter.ttk import *
from tkinter import messagebox
import cv2
import PIL.Image, PIL.ImageTk
from threading import Thread
from Lib import face_recognition, face_dataset, face_training, employee_management

def initialize_video_components(width, height):
    try:
        if not os.path.exists(face_recognition.yml_file_path):
            return None, face_recognition.initialize_face_cascade(),\
                face_recognition.initialize_camera(width=width, height=height),\
                face_recognition.initialize_clahe()

        # Nhận diện khuôn mặt (điểm danh)
        recognizer = face_recognition.initialize_recognizer(face_recognition.yml_file_path)
        face_cascade = face_recognition.initialize_face_cascade()
        video = face_recognition.initialize_camera(width=width, height=height)
        clahe = face_recognition.initialize_clahe()  # Khởi tạo CLAHE
        return recognizer, face_cascade, video, clahe
    except Exception as e:
        print(f"[ERROR] Failed to initialize video components: {e}")
        return None, None, None, None

# Khởi tạo các thành phần liên quan đến video
recognizer, face_cascade, video, clahe = initialize_video_components(width=640, height=480)
is_recognizer_initialized = False

def create_video_frame(parent_frame, width, height):
    """Tạo frame để hiển thị video."""
    video_frame = tkinter.Frame(parent_frame)
    video_frame.pack(side=tkinter.LEFT, padx=5, pady=10, fill=tkinter.Y)
    canvas = tkinter.Canvas(video_frame, width=width, height=height)
    canvas.pack()
    return canvas

def create_info_frame(parent_frame):
    """Tạo frame để hiển thị thông tin nhân viên."""
    info_frame = tkinter.Frame(parent_frame, bg='white', height=480)
    info_frame.pack(side=tkinter.TOP, padx=5, pady=(5, 0), fill=tkinter.BOTH, expand=True)

    # Tiêu đề
    info_label = tkinter.Label(info_frame, text="Thông tin điểm danh", font=("Arial", 17, "bold"), bg="white")
    info_label.pack(anchor=tkinter.NW, padx=10, pady=(15, 25))

    # Tạo các hàng/trường để hiển thị từng trường thông tin
    fields = ["Mã nhân viên", "Tên nhân viên", "Phòng ban", "Thời gian", "Trạng thái"]
    labels = {}  # Dictionary lưu các nhãn (Label) cho từng trường

    for field in fields:
        # Tạo khung chứa từng hàng thông tin
        field_frame = tkinter.Frame(info_frame, bg="white")
        field_frame.pack(fill=tkinter.X, padx=10, pady=10)

        # Tên trường
        field_label = tkinter.Label(field_frame, text=field + ":", font=("Arial", 14), bg="white")
        field_label.pack(side=tkinter.LEFT, padx=5)

        # Ô hiển thị thông tin
        value_label = tkinter.Label(
            field_frame, text="Trống", font=("Arial", 13), bg="white", anchor="w",
            relief="flat", bd=0, highlightthickness=0, highlightcolor="black", highlightbackground="black"
        )
        value_label.pack(side=tkinter.RIGHT, fill=tkinter.X, expand=True, padx=5, ipady=5)
        labels[field] = value_label  # Lưu Label vào dictionary để cập nhật sau

    return labels

def create_controls_frame(parent_frame, start_recognition, stop_recognition):
    """Tạo frame chứa các nút chức năng."""
    controls_frame = tkinter.Frame(parent_frame, bg='white')
    controls_frame.pack(side=tkinter.BOTTOM, fill=tkinter.BOTH, padx=5, pady=(0, 5), ipady=5)

    # Tạo một frame cho các nút chức năng để dễ dàng điều khiển
    button_frame = tkinter.Frame(controls_frame, bg='white')
    button_frame.pack(side=tkinter.TOP, fill=tkinter.X, padx=10, pady=10)

    # Tạo nút điều khiển Check-in
    check_in_button = tkinter.Button(
        button_frame, text="Check-in", font=("Arial", 13),
        command=lambda: start_recognition("check_in")
    )
    check_in_button.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X, padx=5, ipady=5)

    # Tạo nút điều khiển Check-out
    check_out_button = tkinter.Button(
        button_frame, text="Check-out", font=("Arial", 13),
        command=lambda: start_recognition("check_out")
    )
    check_out_button.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X, padx=5, ipady=5)

    # Tạo nút dừng nhận diện
    stop_button = tkinter.Button(
        button_frame, text="Dừng", font=("Arial", 13),
        command=stop_recognition
    )
    stop_button.pack(side=tkinter.LEFT, expand=True, fill=tkinter.X, padx=5, ipady=5)

    return controls_frame

def update_info_text(employee, info_labels, check_type):
    """Cập nhật thông tin nhân viên vào các Label."""
    info_labels["Mã nhân viên"].config(text=employee.employee_id if employee else " Trống")
    info_labels["Tên nhân viên"].config(text=employee.name if employee else " Trống")
    info_labels["Phòng ban"].config(text=employee.department if employee else " Trống")

    if check_type == "check_in":
        info_labels["Thời gian"].config(text=employee.check_in_time if employee else " Trống")
        info_labels["Trạng thái"].config(text=employee.status_1 if employee else " Trống")
    elif check_type == "check_out":
        info_labels["Thời gian"].config(text=employee.check_out_time if employee else " Trống")
        info_labels["Trạng thái"].config(text=employee.status_2 if employee else " Trống")

def update_frame(canvas, photo_container, running, parent_window, check_type, info_labels):
    """Hàm cập nhật khung hình video."""
    if not running[0]:
        # Hiển thị ảnh mặc định
        default_img = os.path.join(os.path.dirname(os.path.abspath(__file__)), "default_img", "istockphoto-661804394-1024x1024.jpg")
        img = cv2.imread(default_img)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Chuyển hệ màu
        img = PIL.Image.fromarray(img) # Chuyển đổi sang định dạng PIL
        img = img.resize((520, 465), PIL.Image.Resampling.LANCZOS)  # Sử dụng LANCZOS để làm mịn ảnh
        img = PIL.ImageTk.PhotoImage(image=img) # Chuyển ảnh từ array sang tkinter image và vẽ lên canvas
        photo_container[0] = img  # Cập nhật ảnh mới vào container
        canvas.create_image(0, 0, image=img, anchor=tkinter.NW) # Vẽ ảnh vào canvas hiển thị lên màn hình
        return

    global recognizer, face_cascade, video, clahe, init_count
    img = None

    if recognizer and video is not None:
        # Lấy danh sách nhân viên từ cơ sở dữ liệu
        employee_list = employee_management.EmployeeManagement.fetch_all_employees()
        # Nhận diện khuôn mặt từ camera
        img, employees = face_recognition.recognize_faces_live(video, recognizer, face_cascade, clahe, employee_list)
        # Điểm danh
        for employee in employees:
            # Thực hiện điểm danh dựa trên loại điểm danh (check-in hoặc check-out)
            if check_type == "check_in":
                if employee.check_in():
                    update_info_text(employee, info_labels, check_type="check_in")
                else:
                    update_info_text(employee, info_labels, check_type="check_in")

            elif check_type == "check_out":
                if employee.check_out():
                    update_info_text(employee, info_labels, check_type="check_out")
                else:
                    update_info_text(employee, info_labels, check_type="check_out")


    elif video is not None:
        # Đọc khung hình từ camera
        _, img = video.read() # Chỉ hiển thị khung hình từ camera nếu không có mô hình
        img = cv2.flip(img, 1) # Lật hình ảnh theo chiều ngang

    if img is not None:
        # img = cv2.resize(img, dsize=None, fx=1, fy=1) # resize kích thước của ảnh hiển thị
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Chuyển hệ màu
        img = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(img)) # Chuyển ảnh từ array sang tkinter image và vẽ lên canvas
        photo_container[0] = img  # Cập nhật ảnh mới vào container
        canvas.create_image(0, 0, image=img, anchor=tkinter.NW) # Vẽ ảnh vào canvas hiển thị lên màn hình

    # Sau 15ms thì chạy lại lệnh update_frame
    parent_window.after(15, lambda: update_frame(canvas, photo_container, running, parent_window, check_type, info_labels))

def create_attendance_live_tab(parent_window, width, height):
    attendance_frame = tkinter.Frame(parent_window, bg='lightblue', width=width, height=height)
    attendance_frame.pack(fill=tkinter.BOTH, expand=True)

    # Chia frame thành hai phần (trái - video, phải - thông tin & nút)
    main_frame = tkinter.Frame(attendance_frame)
    main_frame.pack(fill=tkinter.BOTH, expand=True)

    # Lấy độ phân giải của video
    # canvas_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
    # canvas_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Tạo phần bên trái (video)
    canvas_width = 520
    canvas_height = 480
    canvas = create_video_frame(main_frame, canvas_width, canvas_height)

    # Quản lý trạng thái chạy
    photo_container = [None]
    running = [False]

    # Tạo phần bên phải (Chia thông tin và nút)
    right_frame = tkinter.Frame(main_frame, height=canvas_height)
    right_frame.pack(side=tkinter.LEFT, fill=tkinter.BOTH, expand=True, padx=10, pady=10)

    # Tạo phần bên trên hiển thị thông tin nhân viên
    info_labels = create_info_frame(right_frame)

    def start_recognition(check_type):
        global recognizer, is_recognizer_initialized
        """Bắt đầu nhận diện khuôn mặt."""

        # Dừng chức năng hiện tại nếu đang chạy
        if running[0]:
            running[0] = False

        # Đặt lại trạng thái sau 50ms để đảm bảo chuyển đổi hoàn chỉnh
        parent_window.after(50, lambda: begin_recognition(check_type))

    def begin_recognition(check_type):
        global recognizer, is_recognizer_initialized
        """Thực hiện khởi động nhận diện khuôn mặt sau khi chuyển trạng thái."""
        # Khởi tạo nhận diện khuôn mặt nếu cần
        if is_recognizer_initialized and recognizer is None:
            recognizer = face_recognition.initialize_recognizer(face_recognition.yml_file_path)
            is_recognizer_initialized = True
        if recognizer is None:
            messagebox.showwarning("Warning", "Chưa có dữ liệu nhận diện khuôn mặt. Vui lòng thêm dữ liệu!")
            return

        # Bắt đầu trạng thái mới
        running[0] = True
        update_frame(canvas, photo_container, running, parent_window, check_type, info_labels)

    def stop_recognition():
        """Dừng nhận diện khuôn mặt."""
        running[0] = False
        # Hiển thị ảnh mặc định
        default_img = os.path.join(os.path.dirname(os.path.abspath(__file__)), "default_img", "istockphoto-661804394-1024x1024.jpg")
        img = cv2.imread(default_img)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)  # Chuyển hệ màu
        img = PIL.Image.fromarray(img) # Chuyển đổi sang định dạng PIL
        img = img.resize((canvas_width, canvas_height - 15), PIL.Image.Resampling.LANCZOS)  # Sử dụng LANCZOS để làm mịn ảnh
        img = PIL.ImageTk.PhotoImage(image=img) # Chuyển ảnh từ array sang tkinter image và vẽ lên canvas
        photo_container[0] = img  # Cập nhật ảnh mới vào container
        canvas.create_image(0, 0, image=img, anchor=tkinter.NW) # Vẽ ảnh vào canvas hiển thị lên màn hình

    # Tạo phần bên dưới hiển thị các nút điều khiển
    controls_frame = create_controls_frame(right_frame, start_recognition, stop_recognition)

    return attendance_frame, start_recognition, stop_recognition
