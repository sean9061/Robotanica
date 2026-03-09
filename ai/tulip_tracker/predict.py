from ultralytics import YOLO
import cv2
import socket
import json
import numpy as np
# ===== ダッシュボード連携 ここから =====
import http.server
import socketserver
import threading
import time
# ===== ダッシュボード連携 ここまで =====

# ダッシュボードのIPアドレス ← 環境に合わせて変更
DASHBOARD_IP = "127.0.0.1"

# 見事に変換できたMac専用モデルを読み込む！
model = YOLO('best.mlpackage')

# Webカメラを起動 (映らない場合は '1' に変更)
source = 0
results = model(source, stream=True)

# UDP送信の設定 (Unity側は同じポートで受信する)
UNITY_HOST = '192.168.10.2'
UNITY_PORT = 5004
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# ===== ダッシュボード連携 ここから =====
# カメラ映像をダッシュボードへ MJPEG ストリームで配信する (ポート5103)
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

_srv = _MjpegServer(('', 5103), _MjpegHandler)
threading.Thread(target=_srv.serve_forever, daemon=True).start()
print("[MJPEG] tulip stream on :5103")
# ===== ダッシュボード連携 ここまで =====

print("トラッキングを開始します！終了は 'q' キーです。")

# ウィンドウを先に作成してからスライダーを追加
cv2.namedWindow('Tulip Detection (CoreML)')
cv2.createTrackbar('Threshold %', 'Tulip Detection (CoreML)', 80, 100, lambda x: None)

for result in results:
    frame = cv2.flip(result.orig_img, 1)

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
        x1, x2 = w - x2, w - x1   # 左右反転に合わせてx座標を補正
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        cx_norm = round(cx / w, 4)
        cy_norm = round(cy / h, 4)

        # 擬似奥行きを正規化 (チューリップ実幅=4cm固定を利用)
        # bbox横幅が大きい=近い=depth小、小さい=遠い=depth大
        bbox_w = x2 - x1
        bbox_h = y2 - y1

        f = 20
        real_w = 4

        depth_norm = (f * real_w) / bbox_w

        print(f"{label} (conf={conf:.2f}) 中心座標(正規化): ({cx_norm}, {cy_norm}) 奥行き？: {depth_norm}")

        # 正規化した中心座標・奥行きをUnityにUDPで送信
        payload = json.dumps({"detected": True, "x": cx_norm, "y": cy_norm, "w": bbox_w, "h": bbox_h, "conf": round(float(conf), 2)})
        sock.sendto(payload.encode(), (UNITY_HOST, UNITY_PORT))
        # ===== ダッシュボード連携: 検出結果をUDP送信 =====
        sock.sendto(payload.encode(), (DASHBOARD_IP, 5101))
        # ===== ダッシュボード連携 ここまで =====

        # 青い四角を描画 (OpenCVは BGR なので (255, 0, 0) が青)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)

        # ラベルと信頼度を描画
        cv2.putText(frame, text, (x1, y1 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    else:
        # ===== ダッシュボード連携: 未検出をUDP送信 =====
        sock.sendto(json.dumps({"detected": False}).encode(), (DASHBOARD_IP, 5101))
        # ===== ダッシュボード連携 ここまで =====

    # 画面に表示
    cv2.imshow('Tulip Detection (CoreML)', frame)
    # ===== ダッシュボード連携: 映像フレームをMJPEGサーバーに渡す =====
    with _mjpeg_lock:
        _mjpeg_frame = cv2.resize(frame, (640, 360))
    # ===== ダッシュボード連携 ここまで =====

    # 'q' キーで終了
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()