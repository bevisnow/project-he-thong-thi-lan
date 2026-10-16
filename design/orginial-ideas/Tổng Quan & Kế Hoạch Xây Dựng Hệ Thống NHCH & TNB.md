## **1\. TỔNG QUAN HỆ THỐNG**

**\- Tên dự án:** Hệ thống Ngân hàng câu hỏi & Tổ chức thi nội bộ (LAN exam system).

**\- Mục tiêu:** Giúp giáo viên quản lý đề thi theo chủ đề, tạo đề thi linh hoạt theo ma trận kiến thức và tổ chức thi qua mạng nội bộ (LAN) nhanh chóng, chính xác.

**\- Kiến trúc công nghệ đề xuất:**

**\- Backend:** Python (FastAPI/Flask).

**\- Database:** SQLite

**\- Frontend:** HTML, CSS, JavaScript

**\- Giao thức Mạng LAN:** HTTPS Local

**2\. BẢNG KẾ HOẠCH CHI TIẾT CÁC PHÂN HỆ**

### **PHẦN 1: Phần ngân hàng câu hỏi & quản lý đề gốc**

#### **1.1. Quản lý CSDL ngân hàng câu hỏi**

\- Phân loại theo Môn học, Khối lớp, Chủ đề bài học, Bài học

\- Phân loại mức độ nhận thức: _Nhận biết, Thông hiểu, Vận dụng, Vận dụng cao_.

\- Hỗ trợ các dạng câu hỏi: Trắc nghiệm 4 lựa chọn, Trắc nghiệm Đúng/Sai, Trả lời ngắn

#### **1.2. Nhập dữ liệu**

**\- Import từ File (.docx, .xlsx):**

\- Hệ thống cung cấp file mẫu (Template form sẵn).

Giáo viên soạn đề theo đúng định dạng mẫu (ví dụ: dùng thẻ \[Câu\], \[Đáp án\], đánh dấu \* ở đáp án đúng) và đăng lên web.

**\- Tự động nhận diện & soạn thảo trên Web:**

\- Parse tự động nội dung file vừa upload vào bảng chỉnh sửa trực quan.

Cho phép giáo viên trực tiếp sửa nội dung, thêm/xóa câu hỏi, đính kèm hình ảnh/công thức toán học trên giao diện trước khi lưu chính thức vào ngân hàng.

#### **1.3. Tạo đề thi gốc theo ma trận**

\- Giáo viên cấu hình thông số sinh đề gốc:

\- Chọn môn học, chủ đề.

\- Đặt số lượng câu hỏi cho từng mức độ (ví dụ: 10 câu Nhận biết + 10 câu Thông hiểu + 5 câu Vận dụng).

\- Máy tính tự động rút ngẫu nhiên các câu hỏi trong ngân hàng câu hỏi đạt chuẩn ma trận để tạo thành một Đề gốc.

\- Cho phép giáo viên xem trước đề gốc, đổi câu hỏi khác nếu chưa ưng ý và bấm "lưu đề gốc".

### **PHẦN 2: TẠO PHÒNG THI QUA MẠNG LAN & QUẢN LÝ THÍ SINH**

#### **2.1. Quản lý & nhập danh sách thí sinh**

**\- Tải file mẫu excel:** Hệ thống cấp file .xlsx chuẩn gồm các trường: STT, Mã học sinh / SBD, Họ và tên, Lớp, Ngày sinh.

**\- Upload & tự động đối soát:**

\- Giáo viên upload danh sách lớp dự thi lên phòng thi.

\- Hệ thống kiểm tra tính hợp lệ: Cảnh báo nếu trùng Mã học sinh/SBD hoặc thiếu thông tin bắt buộc.

\- Hiển thị Bảng xem trước: để giáo viên xác nhận.

**\- Tùy chỉnh linh hoạt:** Cho phép giáo viên thêm/xóa nhanh học sinh tự do (học sinh thi bù, thi ghép) trực tiếp trên giao diện web.

#### **2.2. Khởi tạo & Cấu hình phòng thi**

**\- Mã QR & HTTPS Local:**

\- Hệ thống tự động lấy IP nội bộ của máy chủ

\- Sinh mã **QR Code** trên màn hình giáo viên/máy chiếu để học sinh quét mã vào thi lập tức.

**\- Cấu hình tham số phòng thi:**

\- Thời gian làm bài (phút), thời gian bắt đầu/kết thúc.

\- Tùy chọn trộn đề: Tự động đảo thứ tự câu hỏi, đảo đáp án và sinh mã đề riêng cho từng học sinh.

\- Khóa phòng thi bằng mật khẩu hoặc giới hạn dải IP.

#### **2.3. Quy trình Đăng nhập & Xác thực Thí sinh**

\- Học sinh quét QR Code sẽ được chuyển đến trang xác thực.

**\- Xác thực theo SBD / Mã học sinh:**

Học sinh nhập **SBD/Mã học sinh** (hoặc chọn từ danh sách Lớp).

Hệ thống đối soát với danh sách Excel đã nhập ở bước 2.1:

Hợp lệ_:_ Hiển thị _"*Chào mừng \[Họ tên\] - Lớp \[Tên lớp\]*"_ Học sinh bấm "Bắt đầu làm bài".

Không hợp lệ_:_ Báo lỗi.

**\- Cơ chế chống đăng nhập trùng:** Khi SBD đã vào làm bài, tài khoản đó bị khóa chặt với thiết bị hiện tại. Máy khác cố tình nhập trùng SBD sẽ bị từ chối truy cập.

### **PHẦN 3: LÀM BÀI, CHẤM ĐIỂM & GIÁM SÁT**

#### **3.1. Giao diện & Trải nghiệm làm bài của học sinh**

**\- Bố cục màn hình:**

**\- Khu vực chính (Trái/Giữa)**_:_ Hiển thị câu hỏi, hình ảnh, công thức và các phương án chọn ().

**\- Bảng điều khiển góc phải**:

\- Đồng hồ đếm ngược thời gian làm bài.

\- Tiến độ: \[số câu đã làm\] / \[tổng số câu\].

\- Sơ đồ danh sách câu hỏi hỗ trợ chuyển nhanh (Màu xám: Chưa làm

Màu xanh: Đã làm | Màu vàng: Đã đánh dấu xem lại).

Nút **"**Đánh dấu câu hỏi**"** để quay lại kiểm tra sau.

**\- Tự động lưu bài tức thì:**

\- Mỗi khi học sinh tích chọn 1 đáp án, client lập tức gửi request về csdl lưu trạng thái.

\- Nếu đứt mạng LAN hoặc lỡ tay bấm F5/thoát trình duyệt, khi truy cập lại hệ thống giữ nguyên các đáp án đã chọn và thời gian còn lại.

#### **3.2. Chấm bài & Màn hình giám sát Giáo viên:**

#### **\- Chấm điểm tự động:** Ngay khi học sinh bấm "nộp bài" (hoặc hết giờ thu bài), Server tự động chấm điểm dựa theo đáp án đề gốc tương ứng với mã đề của học sinh đó

**\- Giám sát điểm danh:** Màn hình giáo viên cập nhật trạng thái trực tiếp dựa trên danh sách Excel:

\- Thống kê: Tổng sĩ số | Chưa vào (Vắng) | Đang làm | Đã nộp bài.

\- Danh sách chi tiết tên học sinh vắng mặt giúp điểm danh nhanh.

**\- Cấp quyền xử lý sự cố:** Bấm "làm bài lại" cho học sinh nếu bị sập nguồn/hỏng máy để học sinh đổi sang máy mới tiếp tục làm bài.

#### **3.3. Báo cáo & Xuất kết quả**

\- Xuất file Excel (.xlsx) chứa kết quả toàn bộ ca thi khớp chính xác với danh sách học sinh đầu vào:

\- Bảng điểm tổng hợp: STT_,_ Mã HS_,_ Họ tên_,_ Lớp_,_ Mã đề_,_ Số câu đúng_,_ Điểm số_,_ Thời gian nộp.

\- Trang phân tích phổ điểm, tỷ lệ làm đúng/sai từng câu hỏi giúp giáo viên đánh giá chất lượng đề thi.

## **III. NÂNG CẤP BẢO MẬT & CHỐNG GIAN LẬN**

## **Ghi nhận thoát tab/ chuyển tab:** Phát hiện khi học sinh chuyển tab hoặc ẩn trình duyệt, phát cảnh báo trên màn hình học sinh và gửi số lần vi phạm về màn hình giám sát giáo viên

1. **Khóa 1 SBD / 1 thiết bị:** Đảm bảo không thể thi hộ hoặc làm bài giùm từ thiết bị khác.
2. **Mã hóa đề thi gửi về client:** Nội dung câu hỏi chỉ được tải về theo từng trang/câu để tránh việc học sinh ấn F12 lấy toàn bộ đề.