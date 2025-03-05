import openai
import streamlit as st
import os
import toml
import base64
import tempfile
import stripe
from openai import OpenAI
from PIL import Image
from io import BytesIO

# Konfigurasi OpenAI API Key
secrets_path = "secrets.toml"
if os.path.exists(secrets_path):
    secrets = toml.load(secrets_path)
    openai_api_key = secrets.get("OPENAI_API_KEY", None)
    stripe_secret_key = secrets.get("STRIPE_SECRET_KEY", None)
else:
    st.error("File secrets.toml tidak ditemukan. Harap buat file tersebut.")
    openai_api_key = None
    stripe_secret_key = None

# Pastikan API key tersedia sebelum inisialisasi klien
if openai_api_key:
    client = openai.Client(api_key=openai_api_key)
else:
    st.error("API Key OpenAI tidak ditemukan. Harap periksa konfigurasi secrets.toml.")

# Fungsi untuk ekstrak teks dari gambar
def extract_text_from_image(image):
    """Ekstrak teks dari gambar menggunakan Tesseract OCR."""
    return pytesseract.image_to_string(image)

# Fungsi analisis gambar menggunakan GPT-4 Turbo Vision
def analyze_image(image):
    """Analisis gambar dengan GPT-4 Turbo Vision."""
    img_bytes = BytesIO()
    image.save(img_bytes, format="PNG")
    img_bytes.seek(0)
    img_base64 = base64.b64encode(img_bytes.getvalue()).decode('utf-8')
    
    response = client.chat.completions.create(
        model="gpt-4-turbo",
        messages=[
            {"role": "system", "content": "Anda adalah AI yang sangat akurat dalam menganalisis gambar dan membaca teks di dalamnya."},
            {"role": "user", "content": [
                {"type": "text", "text": "Silakan analisis gambar ini secara menyeluruh."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_base64}"}}
            ]}
        ]
    )
    return response.choices[0].message.content

# Konfigurasi Streamlit UI
st.title("Analisis Gambar Akurat dengan AI")

uploaded_file = st.file_uploader("Unggah gambar:", type=["png", "jpg", "jpeg"])

if uploaded_file:
    image = Image.open(uploaded_file)
    st.image(image, caption="Gambar yang diunggah", use_column_width=True)
    st.success("Gambar berhasil diunggah!")
    
    if st.button("Analisis Gambar dan Jawaban Soal"):
        extracted_text = extract_text_from_image(image)
        gpt_analysis = analyze_image(image)
        
        st.subheader("Teks yang Ditemukan dalam Gambar:")
        st.text_area("OCR Result:", extracted_text, height=150)
        
        st.subheader("Hasil Analisis AI:")
        st.text_area("Analisis AI:", gpt_analysis, height=300)

# Konfigurasi Stripe
if stripe_secret_key:
    stripe.api_key = stripe_secret_key
else:
    st.error("Kunci API Stripe tidak ditemukan. Pastikan secrets.toml telah dikonfigurasi dengan benar.")

# Simulasi database pengguna premium
premium_users = set()

def process_payment():
    """Membuat sesi checkout Stripe untuk pembayaran."""
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {"name": "Akses Premium GPT"},
                        "unit_amount": 500,
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            success_url="http://localhost:8501/?success=true",
            cancel_url="http://localhost:8501/?canceled=true",
        )
        return session.url
    except stripe.error.AuthenticationError:
        st.error("Kunci API Stripe tidak valid. Harap periksa secrets.toml.")
        return None
    except Exception as e:
        st.error(f"Terjadi kesalahan saat memproses pembayaran: {e}")
        return None

# Verifikasi akses premium berdasarkan email
user_email = st.sidebar.text_input("Masukkan email untuk verifikasi premium")
is_premium = user_email in premium_users

if st.sidebar.button("Beli Akses Premium 💳"):
    payment_url = process_payment()
    if payment_url:
        st.sidebar.markdown(f"[Klik di sini untuk membayar]({payment_url})")

if openai_api_key:
    st.title("Doragonnoid Chatbot")
    st.write("Pilih fitur yang ingin digunakan:")

    option = st.radio("Pilih opsi:", ["Cari Teks", "Unggah Gambar", "Buat Gambar"])

    # Fitur Chat GPT
    if option == "Cari Teks":
        user_input = st.text_area("Masukkan teks:")
        if st.button("Cari"): 
            if user_input:
                try:
                    model = "gpt-4-turbo" if is_premium else "gpt-3.5-turbo"
                    response = client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": user_input}]
                    )
                    reply_text = response.choices[0].message.content
                    st.text_area("Chatbot:", value=reply_text, height=200)
                except openai.OpenAIError as e:
                    st.error(f"Terjadi kesalahan: {e}")
            else:
                st.warning("Harap masukkan teks terlebih dahulu.")

    # Fitur Pembuatan Gambar
    elif option == "Buat Gambar":
        st.subheader("Buat Gambar dengan DALL·E 🎨")
        image_prompt = st.text_input("Masukkan deskripsi gambar:")
        if st.button("Buat Gambar"):
            if image_prompt:
                try:
                    model = "dall-e-3" if is_premium else "dall-e-2"
                    image_response = client.images.create(
                        model=model,
                        prompt=image_prompt,
                        size="1024x1024",
                        n=1
                    )
                    image_url = image_response.data[0].url
                    st.image(image_url, caption="Hasil Gambar", use_container_width=True)
                except openai.OpenAIError as e:
                    st.error(f"Terjadi kesalahan saat membuat gambar: {e}")
            else:
                st.warning("Harap masukkan deskripsi gambar terlebih dahulu.")

    if is_premium:
        st.sidebar.success("Mode Premium Aktif: Menggunakan model GPT-4-Turbo dan DALL·E 3")

else:
    st.stop()
