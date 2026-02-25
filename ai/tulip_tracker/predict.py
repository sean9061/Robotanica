from ultralytics import YOLO
import cv2

# 見事に変換できたMac専用モデルを読み込む！
model = YOLO('best.mlpackage')

# Webカメラを起動 (映らない場合は '1' に変更)
source = 0
results = model(source, stream=True)

print("トラッキングを開始します！終了は 'q' キーです。")

for result in results:
    frame = result.orig_img
    
    # 検出された箱の座標 (xyxy: 左上と右下) を取得
    boxes = result.boxes.xyxy.cpu().numpy()

    for box in boxes:
        x1, y1, x2, y2 = map(int, box)
        
        # 青い四角を描画 (OpenCVは BGR なので (255, 0, 0) が青)
        cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)

    # 画面に表示
    cv2.imshow('Tulip Detection (CoreML)', frame)

    # 'q' キーで終了
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()