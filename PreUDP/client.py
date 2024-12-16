import socket
import time 
import os
import threading # Thêm thư viện thread, dùng để tạo thread
import clientConfig # Thêm file clientConfig.py vào thư mục chứa file server.py

'''
Using IPv4
Coding UDP server
'''

import socket

def receive_file(s, host, port, data, file_path): # Hàm nhận file
    with open(file_path, 'wb') as f: # Mở file ở chế độ ghi nhị phân, with open sẽ tự đóng file sau khi kết thúc block
        if len(data) < 2: # Kiểm tra kích thước dữ liệu nhận được
            s.sendto(b'RESEND', (host, port)) # Yêu cầu server gửi lại nếu dữ liệu không đủ
        elif b'File not found' not in data[0] and b'EOF' not in data[0]: # Kiểm tra dữ liệu nhận được có chứa File not found và EOF không
            s.sendto(b'OK', (host, port)) # Xác nhận đã nhận đủ dữ liệu
            f.write(data[0]) # Ghi dữ liệu vào file
     
def main():
    # Lấy thông tin từ file clientConfig.py
    host = clientConfig.host
    port = clientConfig.port
    file_path = clientConfig.file_path
    
    processed_line = [] # Khởi tạo list để lưu các dòng đã xử lí
    threads = [] # Khởi tạo list để lưu các thread
    while True:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Tạo socket với IPv4 và UDP
        if os.path.getsize('input.txt') == 0: # Kiểm tra độ dài file input.txt
            print("input.txt is empty. Waiting for new files...")
            time.sleep(5)
            continue

        with open('input.txt', 'r') as input_file: # Mở file ở chế độ đọc
            for line in input_file: # Đọc từng dòng trong file
                if line in processed_line: # Kiểm tra dòng đã được xử lí chưa
                    continue
                else:
                    file_name = line.strip() # Xóa kí tự xuống dòng
                    s.sendto(file_name.encode(), (host, port)) # Gửi tên file đến server
                    while True: 
                        data = s.recvfrom(1024 * 16) # Nhận dữ liệu từ server với buffer size = 1024 * 16
                        if b'File not found' in data[0]:  # Kiểm tra file tồn tại
                            print(f"File {file_name} not found on server.")
                            break # Kết thúc vòng lặp
                        if b'EOF' in data[0]: # Kiểm tra dữ liệu nhận được có chứa EOF không
                            print(f"Finished receiving file {file_name}.")
                            break # Kết thúc vòng lặp
                        thread = threading.Thread(target=receive_file, args=(s, host, port, data, file_path + file_name)) # Gọi hàm nhận file
                        threads.append(thread)
                        thread.start()
                        
                    for t in threads: # Chờ tất cả các thread kết thúc
                        t.join()
                    
                    print(f"Received file {file_name} successfully") # Gửi thông báo đã nhận file thành công
                    processed_line.append(line) # Thêm dòng đã xử lí vào list
                        
        print("Waiting for new files...")

        # Trường hợp processing_line quá lớn, có thể xóa đi để giảm bộ nhớ
        if (len(processed_line) > 10000):
            processed_line.clear()

        time.sleep(5) # Đợi 5 giây trước khi kiểm tra lại file mới
          
if __name__ == "__main__":
    main()
    
    



                    
