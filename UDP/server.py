import socket
import time # Thêm thư viện time, dùng để tạo delay
import os # Thêm thư viện os, dùng để thao tác với hệ thống file
import serverConfig # Thêm file serverConfig.py vào thư mục chứa file server.py

'''
Using IPv4
Coding UDP server
'''

def send_file(s, addr, file_path): # Hàm gửi file
    with open(file_path, 'rb') as f: # Mở file ở chế độ đọc nhị phân, with open sẽ tự đóng file sau khi kết thúc block
        while True:
            chunk = f.read(1024) # buffer size = 1024
            if not chunk: # Xử lí trường hợp không còn dữ liệu
                break
            s.sendto(chunk, addr) # Gửi dữ liệu
    s.sendto(b'EOF', addr)  # Gửi tín hiệu kết thúc file
            
def main():

    # Lấy thông tin từ file serverConfig.py
    host = serverConfig.host
    port = serverConfig.port
    file_path = serverConfig.file_path    
    
    processing_line = [] # Khởi tạo list để lưu các dòng đã xử lí
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Tạo socket với IPv4 và UDP
    s.bind((host, port)) # Bind(lắng nghe) địa chỉ và port
    print("UDP server is running...") #Báo hiệu server đang chạy

    while True:
        data, addr = s.recvfrom(1024 * 16) # Nhận dữ liệu từ client với buffer size = 1024 * 16
        print(f"Received request from {addr}") # Gửi thông báo đã nhận yêu cầu từ client
        
        if data.decode(): # Kiểm tra dữ liệu nhận được có giá trị không
            if not os.path.exists(file_path + data.decode()): # Kiểm tra file tồn tại
                s.sendto(b'File not found', addr) # Gửi thông báo file không tồn tại
                continue
            if (file_path + data.decode()) not in processing_line: # Kiểm tra file đã được xử lí chưa
                processing_line.append(file_path + data.decode()) # Thêm file đã xử lí vào list
            with open(file_path + data.decode(), 'rb') as f: # Mở file ở chế độ đọc nhị phân, with open sẽ tự đóng file sau khi kết thúc block
                while True: 
                    chunk = f.read(1024 * 16) # buffer size = 1024 * 16
                    if not chunk:  # Xử lí trường hợp không còn dữ liệu
                        break 
                    while True:
                        s.sendto(chunk, addr) # Gửi dữ liệu
                        data, addr = s.recvfrom(1024 * 16) # Nhận dữ liệu từ client với buffer size = 1024 * 16
                        if data == b'OK':
                            break
        print(f"Sent file to {addr}") # Gửi thông báo đã gửi file thành công
        s.sendto(b'EOF', addr) # Gửi tín hiệu kết thúc file
        time.sleep(5) # Đợi 5 giây trước khi kiểm tra lại file input.txt
        
        # Trường hợp processing_line quá lớn, có thể xóa đi để giảm bộ nhớ
        if (len(processing_line) > 10000):
            processing_line.clear()
        

if __name__ == "__main__": # Chạy hàm main
    main()

