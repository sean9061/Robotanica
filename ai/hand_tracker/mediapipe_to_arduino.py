import cv2                         # OpenCV（カメラ入力・描画・ウィンドウ制御）
import mediapipe as mp             # MediaPipe（手の骨格検出）
import numpy as np                 # NumPy（背景画像生成用）
import serial

ser = serial.Serial("COM12", 115200)


# --- 背景色を RGB で指定（ここを自由に変えられる） ---
BG_COLOR = (0, 100, 100)           # (R, G, B) 黒
# BG_COLOR = (255, 255, 255)       # 白
# BG_COLOR = (0, 128, 255)         # オレンジっぽい

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

            # canvas = background.copy()    # 背景をコピー（毎フレームまっさらにする）
            canvas = frame;
            if isHandTracking:  # 手が検出された場合
                for i, hand_landmarks in enumerate(results.multi_hand_landmarks):   #検出された各手について

                    label = results.multi_handedness[i].classification[0].label
                    if label == "Right":    #右手なら
                        mp_draw.draw_landmarks(
                            canvas,              # 描画先（カメラ画像ではなく背景）
                            hand_landmarks,      # 手のランドマーク情報
                            mp_hands.HAND_CONNECTIONS  # 指の接続線情報
                        )
                        thumb = hand_landmarks.landmark[4]   #親指先端座標
                        #root = hand_landmarks.landmark[5]   #人差し指根本座標
                        index = hand_landmarks.landmark[8]  #人差し指先端座標
                        pos1 = np.array([int(thumb.x * w), int(thumb.y * h)])
                        pos2 = np.array([int(index.x * w), int(index.y * h)])
                        vec = pos2 - pos1
                        center = (pos1 + pos2)/2
                        center = center.astype('int')
                        vrt = np.array([0,-w])
                        angle = int(calc_angle(vec, vrt))
                        angle_8bit = int(np.clip(angle, 0, 255))
                        radius = int(np.linalg.norm(vec)/2)
                        radius_8bit = int(np.clip(radius, 0, 255))
                        packet = bytes([0xFF, isHandTracking, radius_8bit, angle_8bit]) #頭4桁はArduinoでの到着判定用
                        
                        #if ser.out_waiting:    #out_waitingを書くとArduino側でSerial.available()がfalseになる
                        ser.write(packet)     #Arduinoへシリアル通信で送信
                        
                        #if ser.in_waiting:
                        # read = ser.readline().decode().strip()    #受信
                        
                        cv2.putText(canvas, str(angle), pos2, cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0)) 
                        # cv2.putText(canvas, str(packet), (100, 200),cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0))  
                        # cv2.putText(canvas, str(), (100, 300),cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0))  #Arduinoからの受信を表示
                        cv2.line(canvas, pos1, pos2, color=(0, 255, 0))                 #直線を描画
                        cv2.circle(canvas, center, radius, color=(0, 255, 0))    #円を描画
                    else:
                        cv2.putText(canvas, "Use Right Hand", (100, 200),cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0))
            else:
                packet = bytes([0xFF, isHandTracking, 0x00, 0x00]) #頭4桁はArduinoでの到着判定用
                ser.write(packet)
                cv2.putText(canvas, "No Hands Found", (100, 200),cv2.FONT_HERSHEY_SIMPLEX,1.0,(0, 255, 0))  
                
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