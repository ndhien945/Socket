import socket
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
    
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Tạo socket với IPv4 và UDP
    s.bind((host, port)) # Bind(lắng nghe) địa chỉ và port
    print("UDP server is running...") #Báo hiệu server đang chạy

    while True:
        data, addr = s.recvfrom(1024) # Nhận dữ liệu từ client với buffer size = 1024
        print(f"Received request from {addr}") # Gửi thông báo đã nhận yêu cầu từ client
        
        if data.decode(): # Kiểm tra dữ liệu nhận được
            send_file(s, addr, file_path + data.decode()) # Gửi file
            print(f"Sent file to {addr}") # Gửi thông báo đã gửi file thành công

if __name__ == "__main__": # Chạy hàm main
    main()

