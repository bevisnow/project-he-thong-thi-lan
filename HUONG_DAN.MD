# HƯỚNG DẪN CÀI ĐẶT VÀ SỬ DỤNG LANEXAM

## 1. Máy chủ cần chuẩn bị

- Máy Windows cài **Python 3.13** và có kết nối Internet trong lần cài đầu.
- Giải nén toàn bộ dự án vào một thư mục, ví dụ `C:\LanExam`. Không chạy file trực tiếp bên trong ZIP.
- Giữ các thư mục `backend`, `database`, `frontend` và hai file requirements cùng cấp với `setup.bat`.

> **Lưu ý khi tải mới từ GitHub:** `database/data.db` không được Git theo dõi, nên ZIP mới không có tài khoản hoặc dữ liệu. `setup.bat` hiện chỉ cài thư viện và tạo khóa đăng nhập; nó chưa tạo database hay tài khoản admin. Cần quản trị viên chuẩn bị database và tài khoản admin trước khi hệ thống được sử dụng. Không đưa database có dữ liệu học sinh hoặc file `.env` lên GitHub.

## 2. Cài đặt lần đầu trên máy chủ

1. Cài Python 3.13. Khi cài, chọn **Add Python to PATH**.
2. Mở thư mục dự án đã giải nén.
3. Bấm đúp `setup.bat` và chờ cài đặt hoàn tất. Máy cần Internet ở bước này.
4. Script tạo thư mục `.venv` để chứa thư viện riêng của dự án và tạo file `.env` để lưu khóa JWT trên máy chủ.

Chỉ cần chạy `setup.bat` lại khi cài trên máy mới hoặc khi quản trị viên cập nhật requirements.

## 3. Mở server

1. Bấm đúp `chay-server.bat`.
2. Cửa sổ hiện `http://127.0.0.1:8000` để mở trên chính máy chủ và liệt kê các địa chỉ IPv4 của máy.
3. Giữ cửa sổ này mở trong thời gian sử dụng. Để tắt server, nhấn **Ctrl + C**.

Không dùng `0.0.0.0` làm địa chỉ truy cập trong trình duyệt; đó là địa chỉ server dùng để lắng nghe kết nối.

## 4. Giáo viên và học sinh truy cập

Các máy khách không cần cài Python hay tải source code. Chỉ cần kết nối cùng mạng LAN với máy chủ, mở trình duyệt và nhập:

```text
http://<địa-chỉ-IPv4-máy-chủ>:8000/
```

Ví dụ máy chủ có IPv4 là `192.168.1.10`, địa chỉ truy cập là `http://192.168.1.10:8000/`. Nếu Windows hỏi quyền Firewall, chỉ cho phép trên mạng **Private** đáng tin cậy.

Giáo viên đăng nhập bằng tài khoản do quản trị viên cấp. Học sinh vào thi bằng mã phòng và mã học sinh/SBD được giáo viên cung cấp.

## 5. Tài khoản admin và tạo tài khoản giáo viên

- Ứng dụng không có nút tự đăng ký hoặc tạo admin từ giao diện. Để thêm admin vào database đã khởi tạo, dùng file `tao-tk-admin.txt` ở thư mục gốc dự án:
  1. Dừng server bằng **Ctrl + C** và sao lưu `database\data.db`.
  2. Mở PowerShell rồi chuyển đến nơi đã lưu dự án, ví dụ: `cd "C:\he-thong-thi-offline-lan"`. Nếu dự án nằm chỗ khác, thay bằng đường dẫn đó.
  3. Mở `tao-tk-admin.txt`, sao chép toàn bộ nội dung vào PowerShell và nhấn Enter.
  4. Nhập username, họ tên, rồi nhập và xác nhận mật khẩu. Khi gõ mật khẩu, ký tự sẽ không hiện lên màn hình.
  5. Khi báo `Admin account created.`, chạy lại `chay-server.bat` và đăng nhập bằng tài khoản mới.
- Cách này cần `.venv` đã được cài bởi `setup.bat` và database có bảng `users`. Nó chỉ thêm tài khoản vào database hiện có, không khởi tạo database mới.
- Đăng nhập bằng tài khoản có vai trò `admin`; menu **Tài khoản giáo viên** sẽ xuất hiện ở thanh bên. Mở menu này, nhập tên đăng nhập, họ tên và mật khẩu (ít nhất 8 ký tự), rồi bấm **Tạo tài khoản**.
- Form này chỉ tạo tài khoản giáo viên. Muốn tạo thêm admin, lặp lại các bước bằng file `tao-tk-admin.txt` trên máy chủ.
- Nếu đăng nhập được bằng admin nhưng không thấy menu, đăng xuất rồi đăng nhập lại; nhấn **Ctrl + F5** để tải lại giao diện. Nếu bản cài được tải từ GitHub, quản trị viên cần đưa phiên bản frontend có menu admin lên GitHub trước khi tải lại. Không thay đổi quyền tài khoản giáo viên thành admin chỉ để làm menu hiện ra.
- Trường **Địa chỉ máy chủ** trên trang đăng nhập được lưu trong trình duyệt. Nếu thấy vẫn đăng nhập được tài khoản cũ dù bản tải mới không có dữ liệu, kiểm tra địa chỉ này: `http://192.168.1.10:8000` sẽ dùng database của server ở IP đó; `http://127.0.0.1:8000` dùng server chạy trên chính máy đang mở trình duyệt.

## 6. Những lần sử dụng tiếp theo

- Trên máy chủ, chỉ cần chạy `chay-server.bat`; không cần cài lại thư viện.
- Không xóa `.env`: thay khóa sẽ làm các phiên đăng nhập hiện tại hết hiệu lực.
- Không xóa `database\data.db`: đây là dữ liệu hệ thống. Sao lưu file này khi server đã tắt.
- Không gửi `.env`, `database\data.db` hoặc dữ liệu học sinh lên GitHub hay cho người không có quyền.

## 7. Lỗi thường gặp

- **'python' is not recognized:** cài Python 3.13, chọn **Add Python to PATH**, rồi đóng/mở lại File Explorer hoặc Command Prompt.
- **Cài thư viện thất bại:** kiểm tra Internet rồi chạy lại `setup.bat`.
- **Không kết nối được từ máy khác:** kiểm tra hai máy cùng mạng, dùng đúng IPv4 của Wi-Fi/Ethernet, giữ cửa sổ server mở và cho phép cổng 8000 trên Windows Firewall cho mạng Private.
- **Port 8000 đang được sử dụng:** đóng server cũ trước khi mở server mới.
- **Đăng nhập được nhưng không thấy menu Tài khoản giáo viên:** kiểm tra đang đăng nhập đúng tài khoản admin, kiểm tra địa chỉ máy chủ, đăng xuất/đăng nhập lại và nhấn Ctrl + F5. Nếu vẫn mất, kiểm tra GitHub đã có phiên bản frontend mới.
- **Không có bảng hoặc không đăng nhập được trên bản tải sạch:** cần quản trị viên khởi tạo database và tài khoản admin cho bản cài đó; `setup.bat` hiện chưa làm bước này.

## 8. Lưu ý bảo mật

Server đang dùng HTTP trên mạng LAN. Chỉ sử dụng trên mạng trường học đáng tin cậy; không mở cổng 8000 ra Internet công cộng. File `.env` chứa khóa ký token, cần giữ riêng trên máy chủ.
