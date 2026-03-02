from ultralytics import YOLO
import cv2
import socket
import json

# 見事に変換できたMac専用モデルを読み込む！
model = YOLO('best.mlpackage')

# Webカメラを起動 (映らない場合は '1' に変更)
source = 0
results = model(source, stream=True)

# UDP送信の設定 (Unity側は同じポートで受信する)
UNITY_HOST = '127.0.0.1'
UNITY_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("トラッキングを開始します！終了は 'q' キーです。")

# ウィンドウを先に作成してからスライダーを追加
cv2.namedWindow('Tulip Detection (CoreML)')
cv2.createTrackbar('Threshold %', 'Tulip Detection (CoreML)', 80, 100, lambda x: None)

for result in results:
    frame = result.orig_img

    # スライダーの値を信頼度閾値として取得 (0〜100 → 0.0〜1.0)
    threshold = cv2.getTrackbarPos('Threshold %', 'Tulip Detection (CoreML)') / 100.0

    # 検出された箱の座標、クラス、信頼度を取得
    boxes = result.boxes.xyxy.cpu().numpy()
    confs = result.boxes.conf.cpu().numpy()
    clss = result.boxes.cls.cpu().numpy()
    names = result.names

    # 閾値を超えた検出の中で信頼度が最も高い1つだけを選ぶ
    best = max(
        ((box, conf, cls) for box, conf, cls in zip(boxes, confs, clss) if conf >= threshold),
        key=lambda x: x[1],
        default=None,
    )

    if best is not None:
        box, conf, cls = best
        x1, y1, x2, y2 = map(int, box)
        label = names[int(cls)]
        text = f"{label} {conf:.2f}"

        # 中心座標を計算して正規化 (0.0〜1.0)
        h, w = frame.shape[:2]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        cx_norm = round(cx / w, 4)
        cy_norm = round(cy / h, 4)
        print(f"{label} (conf={conf:.2f}) 中心座標(正規化): ({cx_norm}, {cy_norm})")

        # 正規化した中心座標をUnityにUDPで送信
        payload = json.dumps({"x": cx_norm, "y": cy_norm, "conf": round(float(conf), 2)})
        sock.sendto(payload.encode(), (UNITY_HOST, UNITY_PORT))

        # 青い四角を描画 (OpenCVは BGR なので (255, 0, 0) が青)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)

        # ラベルと信頼度を描画
        cv2.putText(frame, text, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    # 画面に表示
    cv2.imshow('Tulip Detection (CoreML)', frame)

    # 'q' キーで終了
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()