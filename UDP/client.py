import socket
import clientConfig # Thêm file clientConfig.py vào thư mục chứa file server.py

'''
Using IPv4
Coding UDP server
'''

import socket

def receive_file(s, file_path): # Hàm nhận file
    with open(file_path, 'wb') as f: # Mở file ở chế độ ghi nhị phân, with open sẽ tự đóng file sau khi kết thúc block
        while True:
            chunk, addr = s.recvfrom(1024) # Nhận dữ liệu từ server với buffer size = 1024
            if chunk == b'EOF': # Xử lí trường hợp kết thúc file, EOF = End Of File
                break
            f.write(chunk) # Ghi dữ liệu vào file

def main():
    # Lấy thông tin từ file clientConfig.py
    host = clientConfig.host
    port = clientConfig.port
    file_path = clientConfig.file_path

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Tạo socket với IPv4 và UDP
    with open('input.txt', 'r') as input_file: # Mở file ở chế độ đọc
        for line in input_file: # Đọc từng dòng trong file
            file_name = line.strip() # Xóa kí tự xuống dòng
            s.sendto(file_name.encode(), (host, port)) # Gửi tên file
            receive_file(s, file_path + file_name) # Nhận file
            print(f"File {file_name} received successfully") # Gửi thông báo đã nhận file thành công
if __name__ == "__main__":
    main()