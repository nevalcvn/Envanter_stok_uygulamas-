import sys
import sqlite3
import os
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QLabel, QTableWidget, 
                             QHeaderView, QDialog, QFormLayout, QComboBox, 
                             QDateEdit, QMessageBox, QTableWidgetItem)
from PyQt5.QtCore import QDate

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
            # Dinamik dosya yolu: Kod neredeyse, veritabanını da o klasörde arar
            mevcut_klasor = os.path.dirname(os.path.abspath(__file__))
            veritabani_yolu = os.path.join(mevcut_klasor, "Envanter_Problemi.db") 
            
            self.conn = sqlite3.connect(veritabani_yolu) 
            self.cursor = self.conn.cursor()
            print(f"Veritabanı bağlantısı başarılı! Konum: {veritabani_yolu}")
        except Exception as e:
            print(f"Veritabanı bağlantı hatası: {e}")

    def arayuz_olustur(self):
        self.sol_menu_layout = QVBoxLayout()
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
            QPushButton:hover {
                background-color: #1976D2;
            }
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
        
        self.tabloyu_guncelle()

    def kategori_butonlari_olustur(self):
        try:
            self.cursor.execute("SELECT Kategori_Adi FROM Categories")
            kategoriler = self.cursor.fetchall()
            
            buton_stili = """
                QPushButton {
                    background-color: #E0E0E0; 
                    color: #333333; 
                    font-weight: bold; 
                    padding: 12px;
                    border-radius: 5px;
                    margin-bottom: 5px;
                }
                QPushButton:hover {
                    background-color: #D0D0D0;
                }
            """

            for kat in kategoriler:
                kategori_adi = kat[0]
                btn = QPushButton(kategori_adi)
                btn.setStyleSheet(buton_stili)
                self.sol_menu_layout.addWidget(btn)
                
        except Exception as e:
            print(f"Kategoriler çekilirken hata oluştu: {e}")

    def yeni_kayit_penceresi_ac(self):
        dialog = UrunAcilisDialog(self.cursor, self.conn)
        if dialog.exec_():
            self.tabloyu_guncelle()

    def tabloyu_guncelle(self):
        self.tablo.setRowCount(0)
        
        try:
            sorgu = """
                SELECT i.Malzeme_Adi, a.Acilis_tarihi, a.Son_kullanma_tarihi, a.Durum 
                FROM Active_Products a
                JOIN Ingredients i ON a.Malzeme_ID = i.ID
                WHERE a.Durum = 'Açık'
            """
            self.cursor.execute(sorgu)
            kayitlar = self.cursor.fetchall()
            
            for satir_indeksi, satir_verisi in enumerate(kayitlar):
                self.tablo.insertRow(satir_indeksi)
                for sutun_indeksi, veri in enumerate(satir_verisi):
                    self.tablo.setItem(satir_indeksi, sutun_indeksi, QTableWidgetItem(str(veri)))
                    
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
