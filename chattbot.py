import openai
import streamlit as st
import os
import toml
import stripe
from openai import OpenAI
from PIL import Image
import pytesseract

# Pastikan Tesseract sudah diinstal dengan benar dan path sesuai
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Pastikan path ini benar

def extract_text_from_image(image):
    # Coba mengekstrak teks dari gambar menggunakan Tesseract
    try:
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        st.error(f"Terjadi kesalahan saat mengekstrak teks: {e}")
        return ""

# Load API key dari secrets.toml
secrets_path = "secrets.toml"
if os.path.exists(secrets_path):
    secrets = toml.load(secrets_path)
    openai_api_key = secrets.get("OPENAI_API_KEY", None)
    stripe_secret_key = secrets.get("STRIPE_SECRET_KEY", None)
else:
    st.error("File secrets.toml tidak ditemukan. Harap buat file tersebut.")
    openai_api_key = None
    stripe_secret_key = None

# Konfigurasi Stripe
if stripe_secret_key:
    stripe.api_key = stripe_secret_key
else:
    st.error("Kunci API Stripe tidak ditemukan. Pastikan secrets.toml telah dikonfigurasi dengan benar.")

# Simulasi database pengguna premium (dapat diganti dengan database nyata)
premium_users = set()

def process_payment(user_email):
    """Membuat sesi checkout Stripe untuk pembayaran."""
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "usd",
                    "product_data": {"name": "Akses Premium GPT"},
                    "unit_amount": 500,
                },
                "quantity": 1,
            }],
            mode="payment",
            success_url=f"http://localhost:8501/?success=true&email={user_email}",
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

# Cek apakah pembayaran sukses dari URL parameter
query_params = st.query_params
if "success" in query_params and "email" in query_params:
    paid_email = query_params["email"]
    premium_users.add(paid_email)
    st.sidebar.success(f"Email {paid_email} sekarang memiliki akses premium!")

# Periksa apakah email sudah terdaftar sebagai pengguna premium
is_premium = user_email in premium_users
if user_email:
    if is_premium:
        st.sidebar.success("Email terverifikasi! Anda memiliki akses premium.")
    else:
        st.sidebar.warning("Email belum terdaftar sebagai pengguna premium. Silakan lakukan pembayaran untuk mendapatkan akses.")

if st.sidebar.button("Beli Akses Premium 💳"):
    if user_email:
        payment_url = process_payment(user_email)
        if payment_url:
            st.sidebar.markdown(f"[Klik di sini untuk membayar]({payment_url})")
    else:
        st.sidebar.error("Masukkan email sebelum membeli akses premium.")

if openai_api_key:
    client = OpenAI(api_key=openai_api_key)
    st.title("Chatbot dengan OpenAI GPT 🚀")
    st.write("Pilih fitur yang ingin digunakan:")

    option = st.radio("Pilih opsi:", ["Cari Teks", "Unggah Gambar", "Buat Gambar", "Unggah Video", "Unggah File"])

    # Fitur Unggah Gambar
    if option == "Unggah Gambar":
        st.subheader("Unggah Gambar untuk Analisis 🖼")
        uploaded_image = st.file_uploader("Unggah gambar", type=["png", "jpg", "jpeg"])
        if uploaded_image and st.button("Analisis Gambar"):
            try:
                # Baca gambar dan lakukan OCR untuk mengekstrak teks
                image = Image.open(uploaded_image)
                extracted_text = extract_text_from_image(image)
                
                # Tampilkan gambar yang diunggah
                st.image(image, caption="Gambar yang diunggah", use_container_width=True)

                # Kirim teks hasil ekstraksi ke GPT untuk mendapatkan jawaban
                if extracted_text:
                    response = client.chat.completions.create(
                        model="gpt-4-turbo" if is_premium else "gpt-3.5-turbo",
                        messages=[{
                            "role": "system", "content": "Anda adalah asisten AI yang membantu mengerjakan soal terkait gambar yang diunggah."
                        }, {
                            "role": "user", "content": f"Teks yang diekstrak: {extracted_text}. Silakan bantu saya menjawab soal terkait gambar ini."
                        }]
                    )
                    result_text = response.choices[0].message.content
                    st.text_area("Hasil Analisis:", value=result_text, height=200)
                else:
                    st.warning("Tidak ada teks yang dapat diekstrak dari gambar.")

            except Exception as e:
                st.error(f"Terjadi kesalahan saat menganalisis gambar: {e}")
    
    if is_premium:
        st.sidebar.success("Mode Premium Aktif: Menggunakan model GPT-4-Turbo dan DALL·E 3")
else:
    st.stop()
