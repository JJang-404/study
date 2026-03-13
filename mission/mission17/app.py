import streamlit as st
import onnxruntime as ort
import numpy as np
import cv2
from streamlit_drawable_canvas import st_canvas
import pandas as pd
import altair as alt

# =============== 성능 최적화 : 모델 캐싱 ===============
@st.cache_resource
def load_model():
    # model/mnist-12.onnx 파일을 메모리에 한 번만 로드합니다.
    return ort.InferenceSession("model/mnist-12.onnx")

session = load_model()

# =============== 후처리 함수 (Softmax) ===============
def softmax(logits):
    e_x = np.exp(logits - np.max(logits))
    return e_x / e_x.sum()

# =============== 추론 실행 함수 ===============
def run_inference(input_tensor):
    input_name = session.get_inputs()[0].name
    output_name = session.get_outputs()[0].name
    logits = session.run([output_name], {input_name: input_tensor})[0]
    probs = softmax(logits[0])
    pred = np.argmax(probs)
    return pred, probs

# =============== 공통 예측 실행 함수 (OCR 기능 포함) ===============
def perform_prediction(canvas_data):
    if canvas_data is not None and np.sum(canvas_data) > 0:
        # 1. 전처리용 그레이스케일 변환 (np.int8 -> np.uint8로 수정)
        image = canvas_data.astype(np.uint8)
        gray = cv2.cvtColor(image, cv2.COLOR_RGBA2GRAY)
        
        # 2. 숫자 영역 분리 (Segmentation)
        _, thresh = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 왼쪽에서 오른쪽 방향으로 숫자 정렬 (그래야 '16'이 '61'이 되지 않음)
        contours = sorted(contours, key=lambda c: cv2.boundingRect(c)[0])
        
        final_results = []
        preprocessed_imgs = []
        
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            
            # 노이즈 제거 (가로/세로 5픽셀 미만 무시)
            if w < 5 or h < 5:
                continue
            
            roi = gray[y:y+h, x:x+w]
            
            # MNIST 규격에 맞춰 정사각형 패딩 추가 및 28x28 리사이즈
            pad = max(w, h) + 20
            padded = np.zeros((pad, pad), dtype=np.uint8)        
            offset_x, offset_y = (pad - w) // 2, (pad - h) // 2
            padded[offset_y:offset_y+h, offset_x:offset_x+w] = roi
            
            resized = cv2.resize(padded, (28, 28), interpolation=cv2.INTER_LINEAR)
            
            # MNIST 표준 정규화 시도
            normalized = (resized.astype(np.float32) / 255.0 - 0.1307) / 0.3081
            input_tensor = normalized.reshape(1, 1, 28, 28)
            
            # 추론
            pred, _ = run_inference(input_tensor)
            
            final_results.append(str(pred))
            preprocessed_imgs.append(resized)
            
        # 3. 결과 출력
        if final_results:
            st.divider()
            result_str = "".join(final_results)
            st.markdown(f"<h1 style='text-align: center; color: #4CAF50;'>인식 결과: {result_str}</h1>", unsafe_allow_html=True)
            
            # 각 자리수 이미지 확인
            cols = st.columns(max(len(preprocessed_imgs), 1))
            for i, img in enumerate(preprocessed_imgs):
                cols[i].image(img, caption=f"Digit {i+1}", use_container_width=True)
        else:
            st.warning("숫자를 조금 더 크고 명확하게 그려주세요!")

# =============== 메인 UI 레이아웃 ===============
st.title("당신의 악필도 AI에겐 정자체! 어디 한번 써보실래요? 😝")

auto_predict = st.toggle("실시간 예측 모드 활성화", value=False)
st.write("거침없이 읽어냅니다. 캔버스에 크게 그려주세요!")

# 캔버스 설정
canvas_result = st_canvas(
    stroke_width=30,           
    stroke_color="#FFFFFF", 
    background_color="#000000", 
    height=300,
    width=600, # 여러 숫자를 위해 가로를 조금 넓혔습니다.
    drawing_mode="freedraw",
    key="mnist_canvas",        
    update_streamlit=True,
)

# 결과 처리 로직
if auto_predict:
    perform_prediction(canvas_result.image_data)
else:
    if st.button("결과 예측"):
        perform_prediction(canvas_result.image_data)
