import sys
import sqlite3
import os
from datetime import datetime, date
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTableWidget, 
                             QHeaderView, QDialog, QFormLayout, QComboBox, 
                             QDateEdit, QMessageBox, QTableWidgetItem)
from PyQt5.QtCore import QDate
from PyQt5.QtGui import QColor # Hücreleri boyamak için gerekli kütüphane

# ---------------------------------------------------------
# 1. YENİ KAYIT PENCERESİ (DIALOG) SINIFI
# ---------------------------------------------------------
class UrunAcilisDialog(QDialog):
    def __init__(self, db_cursor, db_conn):
        super().__init__()
        self.setWindowTitle("Yeni Paket Aç")
        self.setFixedSize(350, 200)
        
        self.cursor = db_cursor
        self.conn = db_conn

        self.layout = QFormLayout(self)

        self.combo_malzeme = QComboBox()
        self.malzemeleri_yukle()
        self.layout.addRow("Malzeme Seç:", self.combo_malzeme)

        self.date_acilis = QDateEdit()
        self.date_acilis.setCalendarPopup(True)
        self.date_acilis.setDate(QDate.currentDate())
        self.layout.addRow("Açılış Tarihi:", self.date_acilis)

        self.btn_kaydet = QPushButton("Kaydet ve Sistemi Güncelle")
        self.btn_kaydet.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        self.btn_kaydet.clicked.connect(self.kayit_islemi)
        self.layout.addRow(self.btn_kaydet)

    def malzemeleri_yukle(self):
        try:
            self.cursor.execute("SELECT ID, Malzeme_Adi FROM Ingredients")
            malzemeler = self.cursor.fetchall()
            for m_id, m_adi in malzemeler:
                self.combo_malzeme.addItem(m_adi, m_id) 
        except Exception as e:
            print(f"Malzemeler yüklenemedi: {e}")

    def kayit_islemi(self):
        secilen_id = self.combo_malzeme.currentData()
        acilis_tarihi_qdate = self.date_acilis.date()
        
        try:
            self.cursor.execute("SELECT Tazelik_omru_gun FROM Ingredients WHERE ID = ?", (secilen_id,))
            sonuc = self.cursor.fetchone()
            
            if sonuc and sonuc[0]:
                tazelik_omru = sonuc[0]
                
                skt_qdate = acilis_tarihi_qdate.addDays(tazelik_omru)
                acilis_str = acilis_tarihi_qdate.toString("yyyy-MM-dd")
                skt_str = skt_qdate.toString("yyyy-MM-dd")
                
                self.cursor.execute("""
                    INSERT INTO Active_Products (Malzeme_ID, Acilis_tarihi, Son_kullanma_tarihi, Durum)
                    VALUES (?, ?, ?, 'Açık')
                """, (secilen_id, acilis_str, skt_str))
                
                self.conn.commit()
                QMessageBox.information(self, "Başarılı", f"Ürün başarıyla açıldı!\nSon Kullanma Tarihi: {skt_str} olarak belirlendi.")
                self.accept() 
            else:
                QMessageBox.warning(self, "Hata", "Bu ürünün veritabanında 'Tazelik Ömrü' değeri girilmemiş!")
                
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Kayıt sırasında bir hata oluştu: {e}")

# ---------------------------------------------------------
# 2. ANA UYGULAMA PENCERESİ SINIFI
# ---------------------------------------------------------
class EnvanterTakipUygulamasi(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kafem - Depo ve Envanter Yönetimi")
        self.setGeometry(100, 100, 900, 600)

        self.db_baglan()

        self.merkez_widget = QWidget()
        self.setCentralWidget(self.merkez_widget)
        self.ana_layout = QHBoxLayout(self.merkez_widget)

        self.arayuz_olustur()

    def db_baglan(self):
        try:
            mevcut_klasor = os.path.dirname(os.path.abspath(__file__))
            veritabani_yolu = os.path.join(mevcut_klasor, "Envanter_Problemi.db") 
            
            self.conn = sqlite3.connect(veritabani_yolu) 
            self.cursor = self.conn.cursor()
            print(f"Veritabanı bağlantısı başarılı! Konum: {veritabani_yolu}")
        except Exception as e:
            print(f"Veritabanı bağlantı hatası: {e}")

    def arayuz_olustur(self):
        self.sol_menu_layout = QVBoxLayout()
        
        # Tümünü Göster Butonu
        self.btn_tumunu_goster = QPushButton("TÜMÜNÜ GÖSTER")
        self.btn_tumunu_goster.setStyleSheet("""
            QPushButton {
                background-color: #757575; 
                color: white; 
                font-weight: bold; 
                padding: 12px;
                border-radius: 5px;
                margin-bottom: 10px;
            }
            QPushButton:hover { background-color: #616161; }
        """)
        self.btn_tumunu_goster.clicked.connect(lambda: self.tabloyu_guncelle(kategori=None))
        self.sol_menu_layout.addWidget(self.btn_tumunu_goster)
        
        # Dinamik Kategori Butonları
        self.kategori_butonlari_olustur()
        self.sol_menu_layout.addStretch() 
        
        self.btn_yeni_kayit = QPushButton("+ YENİ PAKET AÇ")
        self.btn_yeni_kayit.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; 
                color: white; 
                font-weight: bold; 
                padding: 15px;
                border-radius: 5px;
                margin-top: 10px;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        self.btn_yeni_kayit.clicked.connect(self.yeni_kayit_penceresi_ac)
        self.sol_menu_layout.addWidget(self.btn_yeni_kayit)

        self.sag_panel_layout = QVBoxLayout()
        self.baslik = QLabel("Aktif Ürünler ve Tazelik Durumu")
        self.baslik.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        
        self.tablo = QTableWidget(0, 4) 
        self.tablo.setHorizontalHeaderLabels(["Ürün Adı", "Açılış Tarihi", "Son Kullanma", "Durum"])
        self.tablo.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        self.sag_panel_layout.addWidget(self.baslik)
        self.sag_panel_layout.addWidget(self.tablo)

        self.ana_layout.addLayout(self.sol_menu_layout, 1) 
        self.ana_layout.addLayout(self.sag_panel_layout, 4) 
        
        self.tabloyu_guncelle(kategori=None)

    def kategori_butonlari_olustur(self):
        try:
            self.cursor.execute("SELECT Kategori_Adi FROM Categories")
            kategoriler = self.cursor.fetchall()
            
            for kat in kategoriler:
                kategori_adi = kat[0]
                
                arkaplan_rengi = "#E0E0E0" 
                metin_rengi = "#333333"
                
                if "matcha" in kategori_adi.lower():
                    arkaplan_rengi = "#93C572" 
                    metin_rengi = "black"
                elif "kahve" in kategori_adi.lower():
                    arkaplan_rengi = "#D2B48C" 
                    metin_rengi = "black"
                elif "çay" in kategori_adi.lower() or "tea" in kategori_adi.lower():
                    arkaplan_rengi = "#FFB347" 
                    metin_rengi = "black"

                buton_stili = f"""
                    QPushButton {{
                        background-color: {arkaplan_rengi}; 
                        color: {metin_rengi}; 
                        font-weight: bold; 
                        padding: 12px;
                        border-radius: 5px;
                        margin-bottom: 5px;
                    }}
                    QPushButton:hover {{
                        opacity: 0.8;
                    }}
                """
                
                btn = QPushButton(kategori_adi)
                btn.setStyleSheet(buton_stili)
                
                btn.clicked.connect(lambda checked, k=kategori_adi: self.tabloyu_guncelle(kategori=k))
                self.sol_menu_layout.addWidget(btn)
                
        except Exception as e:
            print(f"Kategoriler çekilirken hata oluştu: {e}")

    def yeni_kayit_penceresi_ac(self):
        dialog = UrunAcilisDialog(self.cursor, self.conn)
        if dialog.exec_():
            self.tabloyu_guncelle(kategori=None)

    def tabloyu_guncelle(self, kategori=None):
        self.tablo.setRowCount(0)
        bugun = date.today() # Tarih kıyaslaması için bugünün tarihi
        
        try:
            if kategori is None:
                sorgu = """
                    SELECT i.Malzeme_Adi, a.Acilis_tarihi, a.Son_kullanma_tarihi, a.Durum 
                    FROM Active_Products a
                    JOIN Ingredients i ON a.Malzeme_ID = i.ID
                    WHERE a.Durum = 'Açık'
                """
                self.cursor.execute(sorgu)
            else:
                sorgu = """
                    SELECT i.Malzeme_Adi, a.Acilis_tarihi, a.Son_kullanma_tarihi, a.Durum 
                    FROM Active_Products a
                    JOIN Ingredients i ON a.Malzeme_ID = i.ID
                    JOIN Categories c ON i.Kategori_ID = c.ID
                    WHERE a.Durum = 'Açık' AND c.Kategori_Adi = ?
                """
                self.cursor.execute(sorgu, (kategori,))
                self.baslik.setText(f"Aktif Ürünler: {kategori}")

            if kategori is None:
                self.baslik.setText("Tüm Aktif Ürünler ve Tazelik Durumu")

            kayitlar = self.cursor.fetchall()
            
            for satir_indeksi, satir_verisi in enumerate(kayitlar):
                self.tablo.insertRow(satir_indeksi)
                
                # Son Kullanma Tarihi analiz kısmı (satir_verisi[2] -> Son_kullanma_tarihi sütunudur)
                skt_str = satir_verisi[2]
                kalan_gun = None
                
                try:
                    # Metin olan tarihi Python tarih nesnesine dönüştür
                    skt_tarihi = datetime.strptime(skt_str, "%Y-%m-%d").date()
                    kalan_gun = (skt_tarihi - bugun).days
                except Exception as e:
                    print(f"Tarih ayrıştırma hatası: {e}")

                for sutun_indeksi, veri in enumerate(satir_verisi):
                    item = QTableWidgetItem(str(veri))
                    
                    # AKILLI RENKLENDİRME MANTIĞI
                    if kalan_gun is not None:
                        if kalan_gun <= 0:
                            # Tarihi geçmişse: Hafif Pastel Kırmızı
                            item.setBackground(QColor("#FFCDD2"))
                        elif kalan_gun <= 3:
                            # 3 gün veya daha az kalmışsa: Hafif Pastel Turuncu/Sarı
                            item.setBackground(QColor("#FFE082"))
                            
                    self.tablo.setItem(satir_indeksi, sutun_indeksi, item)
                    
        except Exception as e:
            print(f"Tablo güncellenirken hata oluştu: {e}")

# ---------------------------------------------------------
# 3. UYGULAMAYI ÇALIŞTIRMA KISMI
# ---------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    pencere = EnvanterTakipUygulamasi()
    pencere.show()
    sys.exit(app.exec_())