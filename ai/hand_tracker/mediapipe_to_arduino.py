import cv2                         # OpenCV（カメラ入力・描画・ウィンドウ制御）
import mediapipe as mp             # MediaPipe（手の骨格検出）
import numpy as np                 # NumPy（背景画像生成用）
import serial

ser = serial.Serial("COM7", 115200)


# --- 背景色を RGB で指定（ここを自由に変えられる） ---
BG_COLOR = (0, 100, 100)           # (R, G, B) 黒
# BG_COLOR = (255, 255, 255)       # 白
# BG_COLOR = (0, 128, 255)         # オレンジっぽい

# --- WEBカメラ繋いだらたぶん1に変える ---
cap = cv2.VideoCapture(0)          # デフォルトカメラ（0番）を開く

# カメラ解像度を「要求」する（通らないこともある）
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

mp_hands = mp.solutions.hands      # 手検出モジュールへのショートカット
mp_draw = mp.solutions.drawing_utils  # 骨格描画ユーティリティ

ntrl = np.array([128,128,128])               #サーボ中心

def main():
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
            isHandTracking = bool(results.multi_hand_landmarks) # 検出されたかどうか

            # frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY) # グレースケールできない
            # canvas = background.copy()    # 背景をコピー（毎フレームまっさらにする）
            canvas = frame
            if isHandTracking:  # 手が検出された場合
                for i, hand_landmarks in enumerate(results.multi_hand_landmarks):   #検出された各手について

                    label = results.multi_handedness[i].classification[0].label
                    if label == "Right":    #右手なら
                        mp_draw.draw_landmarks(
                            canvas,              # 描画先（カメラ画像ではなく背景）
                            hand_landmarks,      # 手のランドマーク情報
                            mp_hands.HAND_CONNECTIONS  # 指の接続線情報
                        )
                        
                        # 座標から必要値計算
                        wrist = hand_landmarks.landmark[0]  #手首座標
                        thumb_tip = hand_landmarks.landmark[4]   #親指先端座標
                        index_mcp = hand_landmarks.landmark[5]   #人差し指根本座標
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
                        angle = int(calc_angle(vec1, vrt))
                        radius = np.linalg.norm(vec1)/2
                        radius_norm = np.linalg.norm(vec2)/2
                        rad = int(radius)    # 描画用
                        radius = np.clip(radius / radius_norm, 0, 1) #0~1に
                        
                        # どちらかコメントアウトコメントアウト可
                        # radius = 255 * (1 - radius)
                        radius = int(128 + 128*np.cos(np.pi * radius)) #弾性体みたいにrの両端での変化をなだらかにしたい

                        # シリアル通信用
                        angle_8bit = int(np.clip(angle, 0, 255))                        
                        radius_8bit = int(np.clip(radius, 0, 255))
                        packet = bytes([0xFF, isHandTracking, radius_8bit, angle_8bit]) #頭4桁はArduinoでの到着判定用
                        
                        cv2.putText(canvas, str(radius), pos2, cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0)) 
                        # cv2.putText(canvas, str(packet), (100, 200),cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0))  
                        # cv2.putText(canvas, str(), (100, 300),cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0))  #Arduinoからの受信を表示
                        cv2.line(canvas, pos1, pos2, color=(0, 255, 0))                 #直線を描画
                        cv2.circle(canvas, center, rad, color=(0, 255, 0))    #円を描画
                    else:
                        packet = bytes([0xFF, isHandTracking, 0x00, 0x00]) #頭4桁はArduinoでの到着判定用
                        cv2.putText(canvas, "Use Right Hand", (100, 200),cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0))
            else:
                packet = bytes([0xFF, isHandTracking, 0x00, 0x00]) #頭4桁はArduinoでの到着判定用
                cv2.putText(canvas, "No Hands Found", (100, 200),cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0))  
                
            #if ser.out_waiting:    #out_waitingを書くとArduino側でSerial.available()がfalseになる
            ser.write(packet)     #Arduinoへシリアル通信で送信
            #if ser.in_waiting:
            # read = ser.readline().decode().strip()    #受信

            cv2.imshow("MediaPipe Hands", canvas)  # 画面表示
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

# --- 使わない ---
#極座標からサーボ制御量
def servo_control(r, theta, neutral, gain):
    thirds = np.radians([0, 120, 240])                         #モーター位置(3分割)
    contributions = [r * np.cos(theta - t) for t in thirds]     #投影から貢献度を算出
    mean = sum(contributions)/3
    offsets = [c - mean for c in contributions]                 #平均除去:引っ張りすぎないため
    servos = [int(neutral[i] + gain * offsets[i]) for i in range(3)] #制御量算出
    servos = np.clip(servos, 0, 255)    #8ビットに丸め込み
    return servos

main()