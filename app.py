import flet as ft
import requests
import speech_recognition as sr
from rapidfuzz import fuzz
import asyncio
from urllib.parse import urlsplit
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse

VOICE_RESULTS = {}

TURKCE_SURE_ADLARI = {
    1: "Fâtiha", 2: "Bakara", 3: "Âl-i İmrân", 4: "Nisâ", 5: "Mâide", 6: "En'âm", 7: "A'râf", 8: "Enfâl", 9: "Tevbe", 10: "Yûnus",
    11: "Hûd", 12: "Yûsuf", 13: "Ra'd", 14: "İbrâhîm", 15: "Hicr", 16: "Nahl", 17: "İsrâ", 18: "Kehf", 19: "Meryem", 20: "Tâhâ",
    21: "Enbiyâ", 22: "Hac", 23: "Mü'minûn", 24: "Nûr", 25: "Furkân", 26: "Şuarâ", 27: "Neml", 28: "Kasas", 29: "Ankebût", 30: "Rûm",
    31: "Lokmân", 32: "Secde", 33: "Ahzâb", 34: "Sebe'", 35: "Fâtır", 36: "Yâsîn", 37: "Sâffât", 38: "Sâd", 39: "Zümer", 40: "Mü'min",
    41: "Fussilet", 42: "Şûrâ", 43: "Zuhruf", 44: "Duhân", 45: "Câsiye", 46: "Ahkâf", 47: "Muhammed", 48: "Fetih", 49: "Hucurât", 50: "Kâf",
    51: "Zâriyât", 52: "Tûr", 53: "Necm", 54: "Kamer", 55: "Rahmân", 56: "Vâkıa", 57: "Hadîd", 58: "Mücâdele", 59: "Haşr", 60: "Mümtehine",
    61: "Saff", 62: "Cuma", 63: "Münâfikûn", 64: "Tegâbün", 65: "Talâk", 66: "Tahrîm", 67: "Mülk", 68: "Kalem", 69: "Hâkka", 70: "Meâric",
    71: "Nûh", 72: "Cin", 73: "Müzzemmil", 74: "Müddessir", 75: "Kıyâme", 76: "İnsân", 77: "Mürselât", 78: "Nebe'", 79: "Nâziât", 80: "Abese",
    81: "Tekvîr", 82: "İnfitâr", 83: "Mutaffifîn", 84: "İnşikâk", 85: "Bürûc", 86: "Târık", 87: "A'lâ", 88: "Gâşiye", 89: "Fecr", 90: "Beled",
    91: "Şems", 92: "Leyl", 93: "Duhâ", 94: "İnşirâh", 95: "Tîn", 96: "Alak", 97: "Kadir", 98: "Beyyine", 99: "Zilzâl", 100: "Âdiyât",
    101: "Kâria", 102: "Tekâsür", 103: "Asr", 104: "Hümeze", 105: "Fîl", 106: "Kureyş", 107: "Mâûn", 108: "Kevser", 109: "Kâfirûn", 110: "Nasr",
    111: "Tebbet", 112: "İhlâs", 113: "Felak", 114: "Nâs"
}


def main(page: ft.Page):
    page.title = "Kuran-ı Kerim Rehberi"
    page.window.width = 420
    page.window.height = 780
    page.theme_mode = "light"
    page.theme = ft.Theme(color_scheme_seed="teal")
    page.padding = 10

    is_web = getattr(page, "web", False)
    session_id = getattr(page, "session_id", None)

    if session_id is None and hasattr(page, "session") and hasattr(page.session, "id"):
        session_id = page.session.id

    page.appbar = ft.AppBar(
    title=ft.Text("Kuran-ı Kerim", weight="bold", color="white"),
    center_title=True,
    bgcolor="teal",
    elevation=2
)

    tum_ayetler = []
    kuran_verisi_yuklendi = {"hazir": False}

    def kuran_verisini_yukle():
        if kuran_verisi_yuklendi["hazir"]:
            return

        tum_ayetler.clear()

        for sure_no in range(1, 115):
            try:
                cevap = requests.get(
                    f"https://api.alquran.cloud/v1/surah/{sure_no}/editions/quran-uthmani,tr.transliteration,tr.diyanet",
                    timeout=20
                )
                veri = cevap.json()

                if veri.get("code") == 200:
                    arapca_ayetler = veri["data"][0]["ayahs"]
                    okunus_ayetler = veri["data"][1]["ayahs"]
                    meal_ayetler = veri["data"][2]["ayahs"]

                    for i in range(len(arapca_ayetler)):
                        tum_ayetler.append({
                            "sure_no": sure_no,
                            "sure_adi": TURKCE_SURE_ADLARI.get(sure_no, "Bilinmeyen Sure"),
                            "ayet_no": arapca_ayetler[i]["numberInSurah"],
                            "arabic": arapca_ayetler[i]["text"],
                            "okunus": okunus_ayetler[i]["text"],
                            "meal": meal_ayetler[i]["text"],
                        })
            except Exception:
                pass

        kuran_verisi_yuklendi["hazir"] = True

    def metni_normallestir(metin):
        if not metin:
            return ""
        return (
            metin.strip()
            .replace("أ", "ا")
            .replace("إ", "ا")
            .replace("آ", "ا")
            .replace("ة", "ه")
            .replace("ى", "ي")
            .replace("ؤ", "و")
            .replace("ئ", "ي")
            .replace("ً", "")
            .replace("ٌ", "")
            .replace("ٍ", "")
            .replace("َ", "")
            .replace("ُ", "")
            .replace("ِ", "")
            .replace("ّ", "")
            .replace("ْ", "")
            .replace("ـ", "")
        )

    def en_iyi_eslesmeleri_bul(aranan_metin, limit=8):
        aranan = metni_normallestir(aranan_metin)
        sonuclar = []

        for ayet in tum_ayetler:
            ayet_metin = metni_normallestir(ayet["arabic"])

            skor1 = fuzz.ratio(aranan, ayet_metin)
            skor2 = fuzz.partial_ratio(aranan, ayet_metin)
            skor3 = fuzz.token_sort_ratio(aranan, ayet_metin)

            final_skor = max(skor1, skor2, skor3)
            sonuclar.append((final_skor, ayet))

        sonuclar.sort(key=lambda x: x[0], reverse=True)
        return sonuclar[:limit]

    def sure_sonuclarini_grupla(eslesmeler):
        gruplar = {}

        for skor, ayet in eslesmeler:
            sure_no = ayet["sure_no"]

            if sure_no not in gruplar:
                gruplar[sure_no] = {
                    "sure_no": sure_no,
                    "sure_adi": ayet["sure_adi"],
                    "ayetler": [],
                    "en_iyi_skor": skor,
                    "en_iyi_ayet": ayet
                }

            gruplar[sure_no]["ayetler"].append((skor, ayet))

            if skor > gruplar[sure_no]["en_iyi_skor"]:
                gruplar[sure_no]["en_iyi_skor"] = skor
                gruplar[sure_no]["en_iyi_ayet"] = ayet

        gruplanmis = list(gruplar.values())
        gruplanmis.sort(key=lambda x: x["en_iyi_skor"], reverse=True)
        return gruplanmis

    def ayet_listesini_yaz(ayetler):
        ayet_nolari = sorted(set(ayet["ayet_no"] for _, ayet in ayetler))
        return ", ".join(str(n) for n in ayet_nolari)

    def browser_voice_start(mode):
        if not session_id:
            if mode == "search":
                sesli_arama_durum.visible = True
                sesli_arama_durum.value = "❌ Session ID bulunamadı."
                sesli_arama_durum.color = "red"
            else:
                sure_bul_durum.value = "❌ Session ID bulunamadı."
                sure_bul_durum.color = "red"
            page.update()
            return

        try:
            current_url = getattr(page, "url", "")
            parts = urlsplit(current_url)

            if parts.scheme and parts.netloc:
                base_url = f"{parts.scheme}://{parts.netloc}"
            else:
                # Gerekirse kendi Render adresini burada sabitle
                base_url = "https://kuran-rehberi-mwg8.onrender.com"

            voice_url = f"{base_url}/voice?sid={session_id}&mode={mode}"

            page.launch_url(voice_url, web_window_name="_blank")

            if mode == "search":
                sesli_arama_durum.visible = True
                sesli_arama_durum.value = "🎤 Sesli giriş sayfası yeni sekmede açıldı. Açılmazsa popup engelini kontrol et."
                sesli_arama_durum.color = "orange"
            else:
                sure_bul_durum.value = "🎤 Sesli giriş sayfası yeni sekmede açıldı. Açılmazsa popup engelini kontrol et."
                sure_bul_durum.color = "orange"

            page.update()

        except Exception as ex:
            if mode == "search":
                sesli_arama_durum.visible = True
                sesli_arama_durum.value = f"❌ Sesli pencere açılamadı: {ex}"
                sesli_arama_durum.color = "red"
            else:
                sure_bul_durum.value = f"❌ Sesli pencere açılamadı: {ex}"
                sure_bul_durum.color = "red"
            page.update()
    

    def sure_bul_sonuclarini_goster(taninan_metin):
        sure_bul_sonuc_listesi.controls.clear()
        sure_bul_sonuc_listesi.controls.append(
            ft.Row([ft.ProgressRing(color="teal")], alignment=ft.MainAxisAlignment.CENTER)
        )
        page.update()

        try:
            eslesmeler = en_iyi_eslesmeleri_bul(taninan_metin, limit=8)
            gruplanmis_sureler = sure_sonuclarini_grupla(eslesmeler)

            sure_bul_sonuc_listesi.controls.clear()

            if not gruplanmis_sureler:
                sure_bul_sonuc_listesi.controls.append(
                    ft.Text("Eşleşme bulunamadı.", color="red")
                )
            else:
                sure_bul_sonuc_listesi.controls.append(
                    ft.Text("En yakın sure eşleşmeleri:", weight="bold", size=16, color="teal")
                )

                for grup in gruplanmis_sureler[:3]:
                    en_iyi_ayet = grup["en_iyi_ayet"]
                    ayetler_yazisi = ayet_listesini_yaz(grup["ayetler"])

                    kart = ft.Container(
                        bgcolor="#f0fdfa",
                        padding=15,
                        border_radius=10,
                        content=ft.Column(
                            spacing=6,
                            controls=[
                                ft.Text(
                                    f"📖 {grup['sure_adi']} Suresi",
                                    weight="bold",
                                    size=18,
                                    color="teal"
                                ),
                                ft.Text(
                                    f"Eşleşen ayetler: {ayetler_yazisi}",
                                    color="orange",
                                    weight="bold"
                                ),
                                ft.Text(
                                    f"En güçlü eşleşme: {en_iyi_ayet['ayet_no']}. ayet  |  Skor: %{int(grup['en_iyi_skor'])}",
                                    color="#444444"
                                ),
                                ft.Divider(height=1, color="teal"),
                                ft.Text(en_iyi_ayet["arabic"], size=22, text_align=ft.TextAlign.RIGHT),
                                ft.Text(en_iyi_ayet["okunus"], italic=True, weight="bold", size=15, color="black"),
                                ft.Text(en_iyi_ayet["meal"], size=15, color="#424242"),
                                ft.ElevatedButton(
                                    "Bu surenin detayını aç",
                                    icon="menu_book",
                                    bgcolor="teal",
                                    color="white",
                                    on_click=lambda e, s_no=grup["sure_no"], s_adi=grup["sure_adi"]: sure_detayini_getir(s_no, s_adi)
                                )
                            ]
                        )
                    )
                    sure_bul_sonuc_listesi.controls.append(kart)

        except Exception as ex:
            sure_bul_sonuc_listesi.controls.clear()
            sure_bul_sonuc_listesi.controls.append(
                ft.Text(f"Arama hatası: {ex}", color="red")
            )

        page.update()

    async def voice_result_watcher():
        while True:
            if session_id in VOICE_RESULTS:
                payload = VOICE_RESULTS.pop(session_id)
                mode = payload.get("mode")
                text = payload.get("text", "").strip()

                if text:
                    if mode == "search":
                        arama_kutusu.value = text
                        sesli_arama_durum.visible = True
                        sesli_arama_durum.value = f"✅ Anlaşılan metin: '{text}'"
                        sesli_arama_durum.color = "teal"
                        page.update()
                        arama_yap(text)

                    elif mode == "find":
                        sure_bul_durum.value = f"✅ Tanınan metin: {text}"
                        sure_bul_durum.color = "teal"
                        page.update()
                        sure_bul_sonuclarini_goster(text)

            await asyncio.sleep(1)


    # ================= 1. İÇERİK: ARAMA MOTORU =================
    arama_kutusu = ft.TextField(
        label="Aramak istediğiniz kelime...",
        expand=True,
        border_radius=15,
        prefix_icon=ft.Icons.SEARCH,
        filled=True,
        on_submit=lambda e: arama_yap(arama_kutusu.value)
    )

    arama_sonuc_listesi = ft.ListView(expand=True, spacing=15, padding=5)
    arama_hafizasi = {"tam_sonuclar": [], "gosterilen_adet": 0}

    daha_fazla_butonu = ft.ElevatedButton(
        "Daha Fazlasını Gör",
        icon=ft.Icons.EXPAND_MORE,
        bgcolor="teal",
        color="white"
    )

    sesli_arama_durum = ft.Text(
        "",
        size=15,
        weight="bold",
        color="teal",
        text_align=ft.TextAlign.CENTER,
        visible=False
    )

    def daha_fazla_yukle(e):
        daha_fazla_butonu.disabled = True
        page.update()

        baslangic = arama_hafizasi["gosterilen_adet"]
        bitis = baslangic + 50
        siradaki_sonuclar = arama_hafizasi["tam_sonuclar"][baslangic:bitis]

        if daha_fazla_butonu in arama_sonuc_listesi.controls:
            arama_sonuc_listesi.controls.remove(daha_fazla_butonu)

        for sonuc in siradaki_sonuclar:
            sure_no = sonuc["surah"]["number"]
            sure_adi = TURKCE_SURE_ADLARI.get(sure_no, "Bilinmeyen Sure")
            ayet_no = sonuc["numberInSurah"]
            metin = sonuc["text"]

            kart = ft.Container(
    bgcolor="#f0fdfa",
    padding=15,
    border_radius=10,
    content=ft.Column(
        spacing=8,
        controls=[
            ft.Text(f"📖 {sure_adi} Suresi, {ayet_no}. Ayet", weight="bold", size=16, color="teal"),
            ft.Divider(height=1, color="teal"),
            ft.Text(metin, size=15),
            ft.ElevatedButton(
                "Bu surenin tamamını gör",
                icon=ft.Icons.MENU_BOOK,
                bgcolor="teal",
                color="white",
                on_click=lambda e, s_no=sure_no, s_adi=sure_adi: sure_detayini_getir(s_no, s_adi)
            )
        ]
    )
)
            arama_sonuc_listesi.controls.append(kart)

        arama_hafizasi["gosterilen_adet"] += len(siradaki_sonuclar)

        if arama_hafizasi["gosterilen_adet"] < len(arama_hafizasi["tam_sonuclar"]):
            daha_fazla_butonu.disabled = False
            arama_sonuc_listesi.controls.append(daha_fazla_butonu)

        page.update()

    daha_fazla_butonu.on_click = daha_fazla_yukle

    def arama_yap(metin):
        aranan_metin = metin.strip()
        arama_sonuc_listesi.controls.clear()

        if not aranan_metin:
            arama_sonuc_listesi.controls.append(
                ft.Text("Lütfen aramak için geçerli bir kelime girin!", color="red", weight="bold")
            )
            page.update()
            return

        arama_sonuc_listesi.controls.append(
            ft.Row([ft.ProgressRing(color="teal")], alignment=ft.MainAxisAlignment.CENTER)
        )
        page.update()

        try:
            cevap = requests.get(
                f"https://api.alquran.cloud/v1/search/{aranan_metin}/all/tr.diyanet",
                timeout=20
            )
            veri = cevap.json()
            arama_sonuc_listesi.controls.clear()

            if veri.get("code") == 200:
                arama_hafizasi["tam_sonuclar"] = veri["data"]["matches"]
                arama_hafizasi["gosterilen_adet"] = 0

                if len(arama_hafizasi["tam_sonuclar"]) == 0:
                    arama_sonuc_listesi.controls.append(
                        ft.Text("Eşleşen bir ayet bulunamadı.", text_align=ft.TextAlign.CENTER, color="grey")
                    )
                else:
                    arama_sonuc_listesi.controls.append(
                        ft.Text(
                            f"✨ Toplam {len(arama_hafizasi['tam_sonuclar'])} sonuç bulundu",
                            weight="bold",
                            size=16,
                            color="teal"
                        )
                    )
                    daha_fazla_yukle(None)
            else:
                arama_sonuc_listesi.controls.append(ft.Text("Eşleşen Sonuç Bulunamadı!", color="red"))

        except Exception:
            arama_sonuc_listesi.controls.clear()
            arama_sonuc_listesi.controls.append(ft.Text("Bağlantı Hatası!", color="red"))

        page.update()

    def arama_buton_tiklandi(e):
        arama_yap(arama_kutusu.value)

    def sesli_arama_worker():
        r = sr.Recognizer()
        metin = ""

        try:
            sesli_arama_durum.visible = True
            sesli_arama_durum.value = "🎤 Dinleniyor..."
            sesli_arama_durum.color = "red"
            sesli_mikrofon_butonu.icon_color = "red"
            sesli_mikrofon_butonu.disabled = True
            page.update()

            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=1)
                audio = r.listen(source, timeout=10, phrase_time_limit=20)

            sesli_arama_durum.value = "⏳ Sesiniz işleniyor..."
            sesli_arama_durum.color = "orange"
            page.update()

            metin = r.recognize_google(audio, language="tr-TR")

            sesli_arama_durum.value = f"✅ Anlaşılan Metin: '{metin}'"
            sesli_arama_durum.color = "teal"
            arama_kutusu.value = metin
            page.update()

        except sr.WaitTimeoutError:
            sesli_arama_durum.visible = True
            sesli_arama_durum.value = "❌ Ses duyulamadı. Çok uzun süre sessiz kaldınız."
            sesli_arama_durum.color = "red"
        except sr.UnknownValueError:
            sesli_arama_durum.visible = True
            sesli_arama_durum.value = "❌ Söylediğiniz anlaşılamadı. Lütfen tekrar deneyin."
            sesli_arama_durum.color = "red"
        except Exception as ex:
            sesli_arama_durum.visible = True
            sesli_arama_durum.value = f"❌ Mikrofon hatası! Detay: {ex}"
            sesli_arama_durum.color = "red"

        sesli_mikrofon_butonu.icon_color = "teal"
        sesli_mikrofon_butonu.disabled = False
        page.update()

        if metin:
            arama_yap(metin)

    def sesli_arama_baslat(e):
        if is_web:
            sesli_arama_durum.visible = True
            sesli_arama_durum.value = "🎤 Tarayıcı sesli giriş penceresi açıldı."
            sesli_arama_durum.color = "orange"
            page.update()
            browser_voice_start("search")
        else:
            page.run_thread(sesli_arama_worker)

    arama_butonu = ft.ElevatedButton(
        "Ara",
        icon=ft.Icons.SEARCH,
        on_click=arama_buton_tiklandi,
        color="white",
        bgcolor="teal",
        height=55
    )

    sesli_mikrofon_butonu = ft.IconButton(
        icon=ft.Icons.MIC,
        icon_color="teal",
        tooltip="Sesle ara",
        on_click=sesli_arama_baslat
    )

    arama_sayfasi_icerik = ft.Column(
        expand=True,
        controls=[
            ft.Row(
                [arama_kutusu, sesli_mikrofon_butonu, arama_butonu],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            sesli_arama_durum,
            ft.Divider(height=10, color="transparent"),
            arama_sonuc_listesi
        ]
    )

    # ================= 2. İÇERİK: SUREYİ BUL =================
    sure_bul_durum = ft.Text(
        "Arapça dua'yı okuyun veya sesini dinletin, en yakın sure/ayet bulunsun.",
        size=16,
        weight="bold",
        color="teal",
        text_align=ft.TextAlign.CENTER
    )

    sure_bul_sonuc_listesi = ft.ListView(expand=True, spacing=15, padding=5)

    def sure_bul_worker():
        r = sr.Recognizer()
        taninan_metin = ""

        try:
            if not kuran_verisi_yuklendi["hazir"]:
                sure_bul_durum.value = "⏳ Kur'an verileri hazırlanıyor, lütfen bekleyin..."
                sure_bul_durum.color = "orange"
                page.update()
                kuran_verisini_yukle()

            sure_bul_durum.value = "🎤 Dinleniyor... Arapça okuyun veya sesi yaklaştırın."
            sure_bul_durum.color = "red"
            sure_bul_butonu.text = "🎤 Dinleniyor..."
            sure_bul_butonu.bgcolor = "red"
            sure_bul_butonu.disabled = True
            page.update()

            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=1)
                audio = r.listen(source, timeout=10, phrase_time_limit=20)

            sure_bul_durum.value = "⏳ Arapça metin çözümleniyor..."
            sure_bul_durum.color = "orange"
            sure_bul_butonu.text = "⏳ İşleniyor..."
            sure_bul_butonu.bgcolor = "orange"
            page.update()

            taninan_metin = r.recognize_google(audio, language="ar-SA")

            sure_bul_durum.value = f"✅ Tanınan metin: {taninan_metin}"
            sure_bul_durum.color = "teal"
            page.update()

        except sr.WaitTimeoutError:
            sure_bul_durum.value = "❌ Ses alınamadı. Çok uzun süre sessiz kalındı."
            sure_bul_durum.color = "red"
        except sr.UnknownValueError:
            sure_bul_durum.value = "❌ Arapça metin anlaşılamadı. Daha net okuyun veya sesi mikrofona yaklaştırın."
            sure_bul_durum.color = "red"
        except Exception as ex:
            sure_bul_durum.value = f"❌ Hata: {ex}"
            sure_bul_durum.color = "red"

        if not taninan_metin:
            sure_bul_butonu.text = "Oku / Dinlet ve Sureyi Bul"
            sure_bul_butonu.bgcolor = "teal"
            sure_bul_butonu.disabled = False
            page.update()
            return

        sure_bul_butonu.text = "🔍 Eşleşmeler Aranıyor..."
        sure_bul_butonu.bgcolor = "blue"
        page.update()

        sure_bul_sonuclarini_goster(taninan_metin)

        sure_bul_butonu.text = "Oku / Dinlet ve Sureyi Bul"
        sure_bul_butonu.bgcolor = "teal"
        sure_bul_butonu.disabled = False
        page.update()

    def sure_bul_baslat(e):
        if is_web:
            sure_bul_durum.value = "🎤 Tarayıcı Arapça ses tanıma penceresi açıldı."
            sure_bul_durum.color = "orange"
            page.update()
            browser_voice_start("find")
        else:
            page.run_thread(sure_bul_worker)

    sure_bul_butonu = ft.ElevatedButton(
        "Oku / Dinlet ve Sureyi Bul",
        icon=ft.Icons.MIC,
        on_click=sure_bul_baslat,
        color="white",
        bgcolor="teal",
        height=55
    )

    sure_bul_sayfasi_icerik = ft.Column(
        expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        controls=[
            ft.Container(height=20),
            sure_bul_butonu,
            ft.Container(height=10),
            sure_bul_durum,
            ft.Divider(height=10, color="transparent"),
            sure_bul_sonuc_listesi
        ]
    )

    # ================= 3. İÇERİK: SURELER LİSTESİ =================
    sureler_listesi_icerik = ft.ListView(expand=True, spacing=10, padding=5)

    # ================= 4. İÇERİK: SURE DETAY =================
    sure_detay_icerik = ft.ListView(expand=True, spacing=15, padding=5)

    def geri_don(e):
        ozel_sekme_cubugu.visible = True
        ana_ekran.content = sureler_listesi_icerik
        page.appbar.title.value = "Kuran-ı Kerim"
        page.update()

    def sure_detayini_getir(sure_no, sure_adi):
        ozel_sekme_cubugu.visible = False
        ana_ekran.content = sure_detay_icerik
        page.appbar.title.value = f"{sure_adi} Suresi"

        sure_detay_icerik.controls.clear()
        sure_detay_icerik.controls.append(
            ft.ElevatedButton("⬅️ Geri Dön", bgcolor="red", color="white", on_click=geri_don)
        )
        sure_detay_icerik.controls.append(
            ft.Row([ft.ProgressRing(color="teal")], alignment=ft.MainAxisAlignment.CENTER)
        )
        page.update()

        try:
            cevap = requests.get(
                f"https://api.alquran.cloud/v1/surah/{sure_no}/editions/tr.transliteration,tr.diyanet",
                timeout=20
            )
            veri = cevap.json()

            sure_detay_icerik.controls.clear()
            sure_detay_icerik.controls.append(
                ft.ElevatedButton("⬅️ Geri Dön", bgcolor="red", color="white", on_click=geri_don)
            )

            if veri.get("code") == 200:
                okunus_ayetleri = veri["data"][0]["ayahs"]
                meal_ayetleri = veri["data"][1]["ayahs"]

                for i in range(len(okunus_ayetleri)):
                    ayet_no = okunus_ayetleri[i]["numberInSurah"]
                    okunus_metni = okunus_ayetleri[i]["text"]
                    meal_metni = meal_ayetleri[i]["text"]

                    kart = ft.Container(
                        bgcolor="#f0fdfa",
                        padding=15,
                        border_radius=10,
                        content=ft.Column(
                            spacing=6,
                            controls=[
                                ft.Text(f"Ayet {ayet_no}", weight="bold", size=14, color="teal"),
                                ft.Text(okunus_metni, italic=True, weight="bold", size=15, color="black"),
                                ft.Text(meal_metni, size=16, color="#424242")
                            ]
                        )
                    )
                    sure_detay_icerik.controls.append(kart)
            else:
                sure_detay_icerik.controls.append(ft.Text("Sure yüklenemedi.", color="red"))
        except Exception:
            sure_detay_icerik.controls.clear()
            sure_detay_icerik.controls.append(
                ft.ElevatedButton("⬅️ Geri Dön", bgcolor="red", color="white", on_click=geri_don)
            )
            sure_detay_icerik.controls.append(ft.Text("Bağlantı Hatası!", color="red"))

        page.update()

    for i in range(1, 115):
        sure_adi = TURKCE_SURE_ADLARI[i]
        satir = ft.Container(
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(f"{i}. {sure_adi} Suresi", weight="bold", size=16, color="black"),
                    ft.Text(">", weight="bold", size=22, color="teal")
                ]
            ),
            bgcolor="white",
            height=60,
            padding=ft.padding.only(left=15, right=15),
            border_radius=10,
            on_click=lambda e, s_no=i, s_adi=sure_adi: sure_detayini_getir(s_no, s_adi)
        )
        sureler_listesi_icerik.controls.append(satir)

    # ================= ANA EKRAN VE SEKMELER =================
    ana_ekran = ft.Container(expand=True, content=arama_sayfasi_icerik)

    def sekmeyi_degistir(sekme_adi):
        arama_sekme_butonu.bgcolor = "teal" if sekme_adi == "arama" else "white"
        arama_sekme_butonu.color = "white" if sekme_adi == "arama" else "teal"

        sure_bul_sekme_butonu.bgcolor = "teal" if sekme_adi == "sure_bul" else "white"
        sure_bul_sekme_butonu.color = "white" if sekme_adi == "sure_bul" else "teal"

        sureler_sekme_butonu.bgcolor = "teal" if sekme_adi == "sureler" else "white"
        sureler_sekme_butonu.color = "white" if sekme_adi == "sureler" else "teal"

        if sekme_adi == "arama":
            ana_ekran.content = arama_sayfasi_icerik
        elif sekme_adi == "sure_bul":
            ana_ekran.content = sure_bul_sayfasi_icerik
        else:
            ana_ekran.content = sureler_listesi_icerik

        page.update()

    arama_sekme_butonu = ft.ElevatedButton(
        "Ara",
        icon=ft.Icons.SEARCH,
        on_click=lambda e: sekmeyi_degistir("arama"),
        bgcolor="teal",
        color="white",
        expand=True
    )

    sure_bul_sekme_butonu = ft.ElevatedButton(
        "Sure Bul",
        icon=ft.Icons.HEARING,
        on_click=lambda e: sekmeyi_degistir("sure_bul"),
        bgcolor="white",
        color="teal",
        expand=True
    )

    sureler_sekme_butonu = ft.ElevatedButton(
        "Sureler",
        icon=ft.Icons.LIST,
        on_click=lambda e: sekmeyi_degistir("sureler"),
        bgcolor="white",
        color="teal",
        expand=True
    )

    ozel_sekme_cubugu = ft.Row(
        [arama_sekme_butonu, sure_bul_sekme_butonu, sureler_sekme_butonu],
        spacing=5
    )

    page.run_task(voice_result_watcher)

    page.add(
        ozel_sekme_cubugu,
        ft.Divider(height=5, color="transparent"),
        ana_ekran
    )


flet_asgi_app = ft.app(target=main, assets_dir="assets", export_asgi_app=True)
app = FastAPI()


@app.get("/voice", response_class=HTMLResponse)
async def voice_page():
    return """
<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <title>Sesli Giriş</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    body {
      font-family: Arial, sans-serif;
      background: #f4f7f7;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
    }
    .box {
      background: white;
      padding: 24px;
      border-radius: 16px;
      box-shadow: 0 10px 30px rgba(0,0,0,.1);
      width: 90%;
      max-width: 420px;
      text-align: center;
    }
    h2 {
      margin-top: 0;
      color: teal;
    }
    p {
      color: #444;
    }
    button {
      background: teal;
      color: white;
      border: 0;
      border-radius: 12px;
      padding: 12px 18px;
      cursor: pointer;
      font-size: 16px;
      margin-top: 12px;
    }
    button:disabled {
      opacity: .6;
      cursor: not-allowed;
    }
    #status {
      margin-top: 18px;
      font-weight: bold;
      color: #333;
      white-space: pre-wrap;
    }
    #result {
      margin-top: 12px;
      color: #0b6;
      font-size: 18px;
    }
  </style>
</head>
<body>
  <div class="box">
    <h2>🎤 Sesli Giriş</h2>
    <p id="modeText">Hazırlanıyor...</p>
    <button id="startBtn">Dinlemeyi Başlat</button>
    <div id="status">Bekleniyor...</div>
    <div id="result"></div>
  </div>

  <script>
    const params = new URLSearchParams(window.location.search);
    const sid = params.get("sid");
    const mode = params.get("mode");

    const modeText = document.getElementById("modeText");
    const statusEl = document.getElementById("status");
    const resultEl = document.getElementById("result");
    const startBtn = document.getElementById("startBtn");

    if (mode === "find") {
      modeText.textContent = "Arapça ses tanıma ile sure/ayet bulma modu";
    } else {
      modeText.textContent = "Türkçe sesli arama modu";
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      statusEl.textContent = "Bu tarayıcı ses tanımayı desteklemiyor. Chrome/Edge kullan.";
      startBtn.disabled = true;
    }

    async function sendResult(text) {
      const res = await fetch("/api/voice-result", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          sid,
          mode,
          text
        })
      });

      if (!res.ok) {
        throw new Error("Sunucuya gönderilemedi.");
      }
    }

    function startRecognition() {
      const recognition = new SpeechRecognition();
      recognition.lang = mode === "find" ? "ar-SA" : "tr-TR";
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      statusEl.textContent = "Dinleniyor...";
      resultEl.textContent = "";
      startBtn.disabled = true;

      recognition.onresult = async (event) => {
        const text = event.results[0][0].transcript;
        resultEl.textContent = "Algılanan metin: " + text;
        statusEl.textContent = "Sunucuya gönderiliyor...";

        try {
          await sendResult(text);
          statusEl.textContent = "Tamamlandı. Bu pencereyi kapatabilirsin.";
        } catch (err) {
          statusEl.textContent = "Hata: " + err.message;
        } finally {
          startBtn.disabled = false;
        }
      };

      recognition.onerror = (event) => {
        statusEl.textContent = "Hata: " + event.error;
        startBtn.disabled = false;
      };

      recognition.onend = () => {
        if (statusEl.textContent === "Dinleniyor...") {
          statusEl.textContent = "Dinleme sona erdi.";
          startBtn.disabled = false;
        }
      };

      recognition.start();
    }

    startBtn.addEventListener("click", startRecognition);
  </script>
</body>
</html>
"""


@app.post("/api/voice-result")
async def voice_result(request: Request):
    data = await request.json()
    sid = data.get("sid")
    mode = data.get("mode")
    text = (data.get("text") or "").strip()

    if not sid or not mode or not text:
        return JSONResponse({"ok": False, "error": "Eksik veri"}, status_code=400)

    VOICE_RESULTS[sid] = {
        "mode": mode,
        "text": text
    }
    return JSONResponse({"ok": True})


app.mount("/", flet_asgi_app)

if __name__ == "__main__":
    ft.app(target=main, assets_dir="assets")
else:
    asgi_app = app