import cv2                         # OpenCV（カメラ入力・描画・ウィンドウ制御）
import mediapipe as mp             # MediaPipe（手の骨格検出）
import numpy as np                 # NumPy（背景画像生成用）
import serial

################################### Macでは書き換える ###################################
SERIAL_PORT = "/dev/tty.usbserial-0001"
cap = cv2.VideoCapture(1)          # デフォルトカメラ（0番）を開く
########################################################################################
import socket

# ===== ダッシュボード連携 ここから =====
import json as _json
import http.server
import socketserver
import threading
import time
# ===== ダッシュボード連携 ここまで =====

# ダッシュボードのIPアドレス ← 環境に合わせて変更
DASHBOARD_IP = "127.0.0.1"

try:
    ser = serial.Serial(SERIAL_PORT, 115200)
except serial.SerialException as e:
    print(f"[Serial ERROR] {e}")
    ser = None
_dash_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ===== ダッシュボード連携 ここから =====
# カメラ映像をダッシュボードへ MJPEG ストリームで配信する (ポート5102)
# ダッシュボードを使わない場合もこのサーバーは無害に動き続ける
_mjpeg_frame = None
_mjpeg_lock  = threading.Lock()

class _MjpegHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
        self.end_headers()
        try:
            while True:
                with _mjpeg_lock:
                    f = _mjpeg_frame
                if f is not None:
                    ok, buf = cv2.imencode('.jpg', f, [cv2.IMWRITE_JPEG_QUALITY, 70])
                    if ok:
                        b = buf.tobytes()
                        self.wfile.write(
                            b'--frame\r\nContent-Type: image/jpeg\r\n'
                            b'Content-Length: ' + str(len(b)).encode() + b'\r\n\r\n'
                        )
                        self.wfile.write(b)
                        self.wfile.write(b'\r\n')
                time.sleep(1 / 30)
        except Exception:
            pass

class _MjpegServer(socketserver.TCPServer):
    allow_reuse_address = True

_srv = _MjpegServer(('', 5102), _MjpegHandler)
threading.Thread(target=_srv.serve_forever, daemon=True).start()
print("[MJPEG] hand stream on :5102")
# ===== ダッシュボード連携 ここまで =====


# --- 背景色を RGB で指定（ここを自由に変えられる） ---
BG_COLOR = (0, 100, 100)           # (R, G, B) 黒
# BG_COLOR = (255, 255, 255)       # 白
# BG_COLOR = (0, 128, 255)         # オレンジっぽい

# カメラ解像度を「要求」する（通らないこともある）
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

mp_hands = mp.solutions.hands      # 手検出モジュールへのショートカット
mp_draw = mp.solutions.drawing_utils  # 骨格描画ユーティリティ

statepos = [100, 100]   #トラッキングステートメント表示座標
ntrl = np.array([128,128,128])               #サーボ中心

def main():
    global _mjpeg_frame
    # --- 最初のフレームで実サイズを確定 ---
    ret, frame = cap.read()            # 1フレームだけ先に取得
    if not ret:                        # 取得に失敗したら
        print("カメラからフレームを取得できませんでした")
        cap.release()                  # カメラ解放
        exit()                         # プログラム終了

    h, w = frame.shape[:2]             # 画像サイズを取得（高さh, 幅w）

    # OpenCVはBGR順なので、RGB → BGR に並び替え
    bg_bgr = (BG_COLOR[2], BG_COLOR[1], BG_COLOR[0])

    # 背景画像を一度だけ生成（全ピクセルを指定色で埋める）
    background = np.full((h, w, 3), bg_bgr, dtype=np.uint8)

    # ウィンドウを作成（サイズ変更可能モード）
    cv2.namedWindow("MediaPipe Hands", cv2.WINDOW_NORMAL)

    # ウィンドウサイズをフレームサイズに固定
    cv2.resizeWindow("MediaPipe Hands", w, h)

    # MediaPipe Hands を初期化
    with mp_hands.Hands(
        max_num_hands=2,               # 最大検出手数
        min_detection_confidence=0.5,  # 検出の信頼度しきい値
        min_tracking_confidence=0.5    # トラッキングの信頼度しきい値
    ) as hands:

        while True:                    # 無限ループ（ESCで抜ける）
            ret, frame = cap.read()    # カメラから1フレーム取得
            if not ret:                # 取得失敗なら
                break                  # ループ終了

            frame = cv2.flip(frame, 1) # 左右反転（鏡映し）
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # BGR → RGB 変換
            results = hands.process(rgb)  # 手の骨格検出を実行
            is_tracking = bool(results.multi_hand_landmarks) # 検出されたかどうか

            # frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # グレースケールできない
            # canvas = background.copy()    # 背景をコピー（毎フレームまっさらにする）
            frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)    #グレースケール
            canvas = cv2.cvtColor(frame_gray, cv2.COLOR_GRAY2BGR)
            
            # 手が検出された場合
            if is_tracking:  
                for i, hand_landmarks in enumerate(results.multi_hand_landmarks):   #検出された各手について

                    label = results.multi_handedness[i].classification[0].label
                    if label == "Right":    #右手なら
                        mp_draw.draw_landmarks(
                            canvas,              # 描画先（カメラ画像ではなく背景）
                            hand_landmarks,      # 手のランドマーク情報
                            mp_hands.HAND_CONNECTIONS,  # 指の接続線情報
                            mp_draw.DrawingSpec(thickness=2, circle_radius=4),
                            mp_draw.DrawingSpec(thickness=2)
                        )
                        
                        # 座標から必要値計算
                        wrist = hand_landmarks.landmark[0]      #手首座標
                        thumb_tip = hand_landmarks.landmark[4]  #親指先端座標
                        index_mcp = hand_landmarks.landmark[5]  #人差し指根本座標
                        index_tip = hand_landmarks.landmark[8]  #人差し指先端座標
                        pos1 = np.array([int(thumb_tip.x * w), int(thumb_tip.y * h)])
                        pos2 = np.array([int(index_tip.x * w), int(index_tip.y * h)])
                        pos3 = np.array([int(wrist.x * w), int(wrist.y * h)])
                        pos4 = np.array([int(index_mcp.x * w), int(index_mcp.y * h)])
                        vec1 = pos2 - pos1
                        vec2 = pos4 - pos3
                        center = (pos1 + pos2)/2
                        center = center.astype('int')
                        vrt = np.array([0,-w])
                        angle_raw = int(calc_angle(vec1, vrt))
                        angle = int(np.clip((angle_raw - 30) * 2,0,360))
                        radius = np.linalg.norm(vec1)/2
                        radius_norm = np.linalg.norm(vec2)/2
                        radpxl = int(radius)    # 描画用
                        radius = np.clip(radius / radius_norm, 0, 1) #0~1に
                        
                        # どちらかコメントアウトコメントアウト可
                        # radius = 255 * (1 - radius)
                        radius = int(128 + 128*np.cos(np.pi * radius)) #弾性体みたいにrの両端での変化をなだらかにしたい

                        # シリアル通信用
                        angle_8bit = int(np.clip(angle * 255 / 360, 0, 255))                        
                        radius_8bit = int(np.clip(radius, 0, 255))
                        packet = bytes([0xFF, is_tracking, radius_8bit, angle_8bit])    #頭4桁はArduinoでの到着判定用
                        packet_str = " ".join(f"0x{b:02X}" for b in packet)             #表示用
                        
                        # 描画
                        textpos = center + [radpxl,-radpxl]
                        cv2.putText(canvas, 
                                    "raw radius: ".ljust(16) + str(radpxl) + "px", 
                                    textpos, cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0),thickness=1)
                        cv2.putText(canvas, 
                                    "inverse radius: ".ljust(16) + str(radius_8bit) + "/255", 
                                    textpos+ (0, 40), cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0),thickness=1)
                        cv2.putText(canvas, 
                                    "raw angle: ".ljust(16) + str(angle_raw) + "degree", 
                                    textpos+ (0, 80), cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0),thickness=1)  
                        cv2.putText(canvas, 
                                    "angle: ".ljust(16) + str(angle) + "degree",
                                    textpos + (0, 120),cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0),thickness=1)  
                        cv2.putText(canvas, 
                                    "packet: ".ljust(16) + packet_str,
                                    textpos + (0, 160),cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0),thickness=1)
                        packet = bytes([0xFF, isHandTracking, radius_8bit, angle_8bit]) #頭4桁はArduinoでの到着判定用
                        
                        #if ser.out_waiting:    #out_waitingを書くとArduino側でSerial.available()がfalseになる
                        if ser: ser.write(packet)     #Arduinoへシリアル通信で送信
                        # ===== ダッシュボード連携: サーボ値・手の位置をUDP送信 =====
                        servo = servo_control(radius, np.radians(angle), ntrl, 1.0)
                        _dash_sock.sendto(_json.dumps({
                            "servo": [int(s) for s in servo],
                            "r": round(float(radius), 1),
                            "theta_deg": round(float(angle), 1),
                            "thumb": [round(thumb_tip.x, 4), round(thumb_tip.y, 4)],
                            "index": [round(index_tip.x, 4), round(index_tip.y, 4)],
                            "detected": True
                        }).encode(), (DASHBOARD_IP, 5100))
                        # ===== ダッシュボード連携 ここまで =====

                        #if ser.in_waiting:
                        # read = ser.readline().decode().strip()    #受信

                        cv2.putText(canvas, str(radius), pos2, cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0))
                        # cv2.putText(canvas, str(packet), (100, 200),cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0))  
                        # cv2.putText(canvas, str(), (100, 300),cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0))  #Arduinoからの受信を表示
                        cv2.line(canvas, pos1, pos2, color=(0, 255, 0), thickness=3)     #直線を描画
                        cv2.circle(canvas, center, radpxl, color=(0, 255, 0), thickness=3)  #円を描画
                    else:
                        mp_draw.draw_landmarks(
                            canvas,                     # 描画先
                            hand_landmarks,             # 手のランドマーク情報
                            mp_hands.HAND_CONNECTIONS,   # 指の接続線情報
                            landmark_drawing_spec=None, # ← 関節を描かない
                        )
                        packet = bytes([0xFF, is_tracking, 0x00, 0x00]) #頭4桁はArduinoでの到着判定用
                        cv2.putText(canvas, "Use Right Hand", statepos,cv2.FONT_HERSHEY_DUPLEX,1.5,(0, 0, 255),thickness=2)
            else:
                packet = bytes([0xFF, is_tracking, 0x00, 0x00]) #頭4桁はArduinoでの到着判定用
                if ser: ser.write(packet)
                # ===== ダッシュボード連携: 未検出をUDP送信 =====
                _dash_sock.sendto(_json.dumps({"detected": False}).encode(), (DASHBOARD_IP, 5100))
                # ===== ダッシュボード連携 ここまで =====
                cv2.putText(canvas, "No Hands Found", statepos,cv2.FONT_HERSHEY_DUPLEX,1.5,(0, 0, 255),thickness=2)

            cv2.imshow("MediaPipe Hands", canvas)  # 画面表示
            # ===== ダッシュボード連携: 映像フレームをMJPEGサーバーに渡す =====
            with _mjpeg_lock:
                _mjpeg_frame = cv2.resize(canvas, (640, 360))
            # ===== ダッシュボード連携 ここまで =====
            if cv2.waitKey(1) & 0xFF == 27:  # ESCキーで終了
                break

    cap.release()                      # カメラ解放
    cv2.destroyAllWindows()            # ウィンドウ全削除

#2つのベクトルのなす角度を計算
def calc_angle(vec1, vec2):
    inner = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    cross = np.cross(vec1, vec2)
    theta = np.degrees(np.arccos(inner/(norm1*norm2)))
    if cross < 0:
        theta *= -1
    return theta + 180

# #--- 使わない ---
# #極座標からサーボ制御量
# def servo_control(r, theta, neutral, gain):
#     thirds = np.radians([0, 120, 240])                         #モーター位置(3分割)
#     contributions = [r * np.cos(theta - t) for t in thirds]     #投影から貢献度を算出
#     mean = sum(contributions)/3
#     offsets = [c - mean for c in contributions]                 #平均除去:引っ張りすぎないため
#     servos = [int(neutral[i] + gain * offsets[i]) for i in range(3)] #制御量算出
#     servos = np.clip(servos, 0, 255)    #8ビットに丸め込み
#     return servos

main()