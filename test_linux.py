from ctypes import CDLL, c_char_p, c_bool

# 共有ライブラリをロード
lib = CDLL("./build/libpamc204.so")

# send_command のシグネチャを設定
# C++側: bool send_command(const std::string& portName, const std::string& command)
# → ctypes では char* として渡す
send_command = lib.send_command
send_command.restype = c_bool
send_command.argtypes = [c_char_p, c_char_p]

# 使用例
port = b"/dev/ttyUSB0"   # Linux のシリアルポート
cmd  = b"E01INF"

ok = send_command(port, cmd)
if not ok:
    print("send_command failed")
else:
    print("send succeeded")