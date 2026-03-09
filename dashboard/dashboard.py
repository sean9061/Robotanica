"""
Kinetic-Botanics リアルタイムダッシュボード
映像: 各トラッカーがJPEG圧縮してUDP送信 → ダッシュボードが受信して表示
データ:
  5100: hand JSON  / 5102: hand JPEG frame
  5101: tulip JSON / 5103: tulip JPEG frame

起動:
    python dashboard/dashboard.py
"""

import argparse
import json
import socket
import threading
import time

import cv2
import numpy as np

# ─────────────────────────────────────────────
#  定数
# ─────────────────────────────────────────────
HAND_UDP_PORT  = 5100
TULIP_UDP_PORT = 5101
PANEL_W, PANEL_H = 640, 360
FRAME_MARGIN = 28          # カメラ映像の余白(px)
WIN_W  = PANEL_W * 2      # 1280
WIN_H  = PANEL_H * 2      # 720
TIMEOUT_SEC = 0.5


# ─────────────────────────────────────────────
#  SharedState
# ─────────────────────────────────────────────
class SharedState:
    def __init__(self):
        self._lock = threading.Lock()

        self.hand_frame  = None   # 受信済みJPEGをデコードしたBGR画像
        self.tulip_frame = None

        # hand tracker データ
        self.servo         = [128, 128, 128]
        self.polar_r       = 0.0
        self.polar_theta   = 0.0
        self.hand_detected = False
        self.last_hand_t   = 0.0
        self.last_hand_frame_t = 0.0

        # tulip tracker データ
        self.tulip_x        = 0.5
        self.tulip_y        = 0.5
        self.tulip_w        = 0
        self.tulip_h        = 0
        self.tulip_conf     = 0.0
        self.tulip_detected = False
        self.last_tulip_t   = 0.0
        self.last_tulip_frame_t = 0.0

    def update_hand(self, d: dict):
        with self._lock:
            self.last_hand_t   = time.time()
            self.hand_detected = d.get("detected", False)
            if self.hand_detected:
                self.servo       = d.get("servo", self.servo)
                self.polar_r     = d.get("r", self.polar_r)
                self.polar_theta = d.get("theta_deg", self.polar_theta)

    def update_tulip(self, d: dict):
        with self._lock:
            self.last_tulip_t   = time.time()
            self.tulip_detected = d.get("detected", False)
            if self.tulip_detected:
                self.tulip_x    = d.get("x", self.tulip_x)
                self.tulip_y    = d.get("y", self.tulip_y)
                self.tulip_w    = d.get("w", self.tulip_w)
                self.tulip_h    = d.get("h", self.tulip_h)
                self.tulip_conf = d.get("conf", self.tulip_conf)

    def set_hand_frame(self, frame: np.ndarray):
        with self._lock:
            self.hand_frame = frame
            self.last_hand_frame_t = time.time()

    def set_tulip_frame(self, frame: np.ndarray):
        with self._lock:
            self.tulip_frame = frame
            self.last_tulip_frame_t = time.time()

    def snapshot(self):
        with self._lock:
            return {
                "hand_frame":        self.hand_frame.copy()  if self.hand_frame  is not None else None,
                "tulip_frame":       self.tulip_frame.copy() if self.tulip_frame is not None else None,
                "servo":             list(self.servo),
                "polar_r":           self.polar_r,
                "polar_theta":       self.polar_theta,
                "hand_detected":     self.hand_detected,
                "last_hand_t":       self.last_hand_t,
                "last_hand_frame_t": self.last_hand_frame_t,
                "tulip_x":           self.tulip_x,
                "tulip_y":           self.tulip_y,
                "tulip_w":           self.tulip_w,
                "tulip_h":           self.tulip_h,
                "tulip_conf":        self.tulip_conf,
                "tulip_detected":    self.tulip_detected,
                "last_tulip_t":      self.last_tulip_t,
                "last_tulip_frame_t": self.last_tulip_frame_t,
            }


# ─────────────────────────────────────────────
#  ヘルパー
# ─────────────────────────────────────────────
def _make_placeholder(text: str, w: int, h: int) -> np.ndarray:
    img = np.full((h, w, 3), 210, dtype=np.uint8)
    tw, th = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)[0]
    cv2.putText(img, text, ((w - tw) // 2, (h + th) // 2),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)
    return img


def _pad_frame(frame: np.ndarray) -> np.ndarray:
    """PANEL_W×PANEL_H のキャンバスに FRAME_MARGIN の余白を付けて映像を配置"""
    inner_w = PANEL_W - FRAME_MARGIN * 2
    inner_h = PANEL_H - FRAME_MARGIN * 2
    canvas = np.full((PANEL_H, PANEL_W, 3), 240, dtype=np.uint8)
    canvas[FRAME_MARGIN:FRAME_MARGIN + inner_h,
           FRAME_MARGIN:FRAME_MARGIN + inner_w] = cv2.resize(frame, (inner_w, inner_h))
    return canvas


# ─────────────────────────────────────────────
#  スレッド: JSON データ受信
# ─────────────────────────────────────────────
def udp_listen_thread(port: int, which: str, shared: SharedState, stop: threading.Event):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.settimeout(0.2)

    while not stop.is_set():
        try:
            data, _ = sock.recvfrom(4096)
            d = json.loads(data.decode())
            if which == "hand":
                shared.update_hand(d)
            else:
                shared.update_tulip(d)
        except socket.timeout:
            continue
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

    sock.close()


# ─────────────────────────────────────────────
#  スレッド: MJPEG ストリームからフレーム受信
# ─────────────────────────────────────────────
def mjpeg_capture_thread(url: str, which: str, shared: SharedState, stop: threading.Event):
    while not stop.is_set():
        cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            time.sleep(1.0)
            continue
        while not stop.is_set():
            ret, frame = cap.read()
            if not ret:
                break
            if which == "hand":
                shared.set_hand_frame(frame)
            else:
                shared.set_tulip_frame(frame)
        cap.release()


# ─────────────────────────────────────────────
#  描画ヘルパー
# ─────────────────────────────────────────────
def draw_bar(canvas: np.ndarray, x: int, y: int, w: int, h: int,
             val: float, max_val: float, color=(80, 200, 80)):
    cv2.rectangle(canvas, (x, y), (x + w, y + h), (205, 205, 205), -1)
    fill = int(w * min(val / max(max_val, 1), 1.0))
    cv2.rectangle(canvas, (x, y), (x + fill, y + h), color, -1)
    cv2.rectangle(canvas, (x, y), (x + w, y + h), (160, 160, 160), 1)


def _dot(canvas: np.ndarray, x: int, y: int, connected: bool):
    color = (30, 160, 30) if connected else (40, 40, 200)
    cv2.circle(canvas, (x, y), 6, color, -1)


# ─────────────────────────────────────────────
#  下段左: サーボバー
# ─────────────────────────────────────────────
def render_servo_panel(snap: dict, w: int, h: int) -> np.ndarray:
    canvas = np.full((h, w, 3), 240, dtype=np.uint8)
    now = time.time()
    connected = (now - snap["last_hand_t"]) < TIMEOUT_SEC

    _dot(canvas, w - 15, 12, connected)
    cv2.putText(canvas, "SERVO BARS", (8, 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (40, 40, 40), 1)

    labels = ["S0", "S1", "S2"]
    colors = [(40, 180, 40), (200, 100, 30), (0, 150, 220)]
    bar_w, bar_h, y_start = w - 100, 22, 35

    for i, (lbl, col) in enumerate(zip(labels, colors)):
        y = y_start + i * 38
        cv2.putText(canvas, lbl, (8, y + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (70, 70, 70), 1)
        draw_bar(canvas, 40, y, bar_w, bar_h, snap["servo"][i], 255, col)
        cv2.putText(canvas, str(snap["servo"][i]),
                    (40 + bar_w + 6, y + 16),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (40, 40, 40), 1)

    y_info = y_start + 3 * 38 + 10
    cv2.putText(canvas, f"r={snap['polar_r']:.1f}  theta={snap['polar_theta']:.1f} deg",
                (8, y_info), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (30, 120, 30), 1)

    return canvas


# ─────────────────────────────────────────────
#  下段右: チューリップ情報
# ─────────────────────────────────────────────
def render_tulip_panel(snap: dict, w: int, h: int) -> np.ndarray:
    canvas = np.full((h, w, 3), 240, dtype=np.uint8)
    now = time.time()
    connected = (now - snap["last_tulip_t"]) < TIMEOUT_SEC

    _dot(canvas, w - 15, 12, connected)
    cv2.putText(canvas, "TULIP METRICS", (8, 18),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (40, 40, 40), 1)

    map_x, map_y, map_size = 12, 30, 120
    cv2.rectangle(canvas, (map_x, map_y), (map_x + map_size, map_y + map_size), (150, 150, 150), 1)
    if snap["tulip_detected"]:
        px = map_x + int(snap["tulip_x"] * map_size)
        py = map_y + int(snap["tulip_y"] * map_size)
        cv2.circle(canvas, (px, py), 5, (0, 120, 220), -1)

    mx, my, line_h = map_x + map_size + 16, map_y + 14, 22

    cv2.putText(canvas, "Conf:", (mx, my), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (70, 70, 70), 1)
    draw_bar(canvas, mx + 48, my - 14, 120, 16, snap["tulip_conf"], 1.0, (0, 120, 220))
    cv2.putText(canvas, f"{snap['tulip_conf']:.2f}",
                (mx + 172, my), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (40, 40, 40), 1)

    my += line_h
    depth = (20 * 4) / snap["tulip_w"] if snap["tulip_w"] > 0 else 0.0
    cv2.putText(canvas, f"Depth: {depth:.1f} cm",
                (mx, my), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (70, 70, 70), 1)

    my += line_h
    cv2.putText(canvas, f"W:{snap['tulip_w']}px  H:{snap['tulip_h']}px",
                (mx, my), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (70, 70, 70), 1)

    my += line_h
    cv2.putText(canvas, f"cx={snap['tulip_x']:.3f}  cy={snap['tulip_y']:.3f}",
                (mx, my), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 120, 30), 1)

    udp_label = "UDP: " + ("●  LIVE" if connected else "●  --")
    cv2.putText(canvas, udp_label, (mx, map_y + map_size - 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48,
                (30, 160, 30) if connected else (40, 40, 200), 1)

    return canvas


# ─────────────────────────────────────────────
#  メインループ: 4パネル合成 → imshow
# ─────────────────────────────────────────────
def display_loop(shared: SharedState, stop: threading.Event):
    cv2.namedWindow("Kinetic-Botanics Dashboard", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Kinetic-Botanics Dashboard", WIN_W, WIN_H)

    hand_placeholder  = _make_placeholder("Waiting for hand tracker...",  PANEL_W, PANEL_H)
    tulip_placeholder = _make_placeholder("Waiting for tulip tracker...", PANEL_W, PANEL_H)

    while not stop.is_set():
        snap = shared.snapshot()
        now  = time.time()

        # フレームタイムアウト時はプレースホルダーを使用、余白付きで配置
        if snap["hand_frame"] is None or (now - snap["last_hand_frame_t"]) > TIMEOUT_SEC:
            left_panel = _pad_frame(hand_placeholder)
        else:
            left_panel = _pad_frame(snap["hand_frame"])
            cv2.putText(left_panel, "HAND TRACKING",
                        (FRAME_MARGIN + 8, FRAME_MARGIN + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (240, 240, 240), 2)

        if snap["tulip_frame"] is None or (now - snap["last_tulip_frame_t"]) > TIMEOUT_SEC:
            right_panel = _pad_frame(tulip_placeholder)
        else:
            right_panel = _pad_frame(snap["tulip_frame"])
            cv2.putText(right_panel, "TULIP DETECTION",
                        (FRAME_MARGIN + 8, FRAME_MARGIN + 22),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (240, 240, 240), 2)

        hand_row  = np.hstack([left_panel,  render_servo_panel(snap, PANEL_W, PANEL_H)])
        tulip_row = np.hstack([right_panel, render_tulip_panel(snap, PANEL_W, PANEL_H)])

        # 境界 (x = PANEL_W) に「画像処理 → 値」を示す矢印を描画
        ay = PANEL_H // 2
        for row in [hand_row, tulip_row]:
            cv2.arrowedLine(row, (PANEL_W - 60, ay), (PANEL_W + 60, ay),
                            (30, 90, 200), 3, tipLength=0.3)
            cv2.putText(row, "解析値", (PANEL_W - 36, ay - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 90, 200), 1)

        canvas = np.vstack([hand_row, tulip_row])

        cv2.imshow("Kinetic-Botanics Dashboard", canvas)

        key = cv2.waitKey(30) & 0xFF
        if key == 27 or key == ord('q'):
            stop.set()
            break

    cv2.destroyAllWindows()


# ─────────────────────────────────────────────
#  エントリポイント
# ─────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Kinetic-Botanics Dashboard")
    parser.add_argument("--hand-host",  default="127.0.0.1",
                        help="hand tracker IP (win2 の IPアドレス)")
    parser.add_argument("--tulip-host", default="127.0.0.1",
                        help="tulip tracker IP (mac3 の IPアドレス)")
    args = parser.parse_args()

    hand_url  = f"http://{args.hand_host}:5102/"
    tulip_url = f"http://{args.tulip_host}:5103/"

    shared = SharedState()
    stop   = threading.Event()

    threads = [
        threading.Thread(target=udp_listen_thread,
                         args=(HAND_UDP_PORT,  "hand",  shared, stop), daemon=True),
        threading.Thread(target=udp_listen_thread,
                         args=(TULIP_UDP_PORT, "tulip", shared, stop), daemon=True),
        threading.Thread(target=mjpeg_capture_thread,
                         args=(hand_url,  "hand",  shared, stop), daemon=True),
        threading.Thread(target=mjpeg_capture_thread,
                         args=(tulip_url, "tulip", shared, stop), daemon=True),
    ]

    for t in threads:
        t.start()

    print("Dashboard started. Press ESC or q to quit.")
    print(f"  Hand  JSON  : UDP 0.0.0.0:{HAND_UDP_PORT}")
    print(f"  Tulip JSON  : UDP 0.0.0.0:{TULIP_UDP_PORT}")
    print(f"  Hand  frame : {hand_url}")
    print(f"  Tulip frame : {tulip_url}")

    display_loop(shared, stop)

    stop.set()
    for t in threads:
        t.join(timeout=1.0)


if __name__ == "__main__":
    main()
