# Google API Kurulum Rehberi

Bu rehber, PHQ-9 depresyon anketi icin Google Forms ve Google Sheets API entegrasyonunu adim adim aciklar.

## 1. Google Cloud Console'da Proje Olusturma

1. [Google Cloud Console](https://console.cloud.google.com/) adresine gidin
2. Ust menude proje secicisine tiklayin > **Yeni Proje** secin
3. Proje adi: `depression-analysis` (veya istediginiz bir isim)
4. **Olustur** butonuna tiklayin

## 2. API'leri Etkinlestirme

1. Sol menuden **API'ler ve Hizmetler** > **Kutuphane** secin
2. Asagidaki API'leri arayip etkinlestirin:
   - **Google Forms API**
   - **Google Sheets API**
   - **Google Drive API**

## 3. OAuth 2.0 Credentials Olusturma

1. **API'ler ve Hizmetler** > **Kimlik Bilgileri** sayfasina gidin
2. **+ Kimlik Bilgisi Olustur** > **OAuth istemci kimligi** secin
3. Oncelikle **Onay ekrani**ni yapilandirmaniz istenirse:
   - Kullanici turu: **Dis** secin
   - Uygulama adi: `Depression Analysis`
   - Destek e-postasi: kendi e-postanizi girin
   - Diger alanlari bos birakin
   - **Kaydet ve Devam Et** tiklayin
4. Kapsam eklemeye gerek yok, devam edin
5. Test kullanicilari bolumune kendi Gmail adresinizi ekleyin
6. OAuth istemci kimligi olusturmaya geri donun:
   - Uygulama turu: **Masaustu uygulamasi** secin
   - Ad: `depression-analysis-client`
   - **Olustur** tiklayin

## 4. Credentials Dosyasini Indirme

1. Olusturulan OAuth 2.0 istemci kimliginin yanindaki **indirme ikonuna** tiklayin
2. JSON dosyasini indirin
3. Dosya adini `credentials.json` olarak degistirin
4. Dosyayi projenin `config/` klasorune kopyalayin:

```bash
cp ~/Downloads/client_secret_*.json ~/depression_analysis_project/config/credentials.json
```

## 5. Ilk Calistirma

Projeyi ilk kez calistirdiginizda tarayicinizda Google hesabi yetkilendirme sayfasi acilacaktir:

```bash
cd ~/depression_analysis_project
python main.py --create-form
```

- Google hesabinizla giris yapin
- Gerekli izinleri verin
- `config/token.json` dosyasi otomatik olusturulacaktir

## 6. Notlar

- `credentials.json` ve `token.json` dosyalarini **asla** Git'e commitlemeyin
- Token suresi doldugunda otomatik yenilenecektir
- Proje "test" modundayken sadece test kullanicilari erisebilir
- Uretim ortami icin Google dogrulamasindan gecmeniz gerekir

## Sorun Giderme

| Sorun | Cozum |
|-------|-------|
| `FileNotFoundError: credentials.json` | `config/credentials.json` dosyasinin var oldugundan emin olun |
| `Access Denied` | Google Cloud Console'da API'lerin etkin oldugundan emin olun |
| `Token expired` | `config/token.json` dosyasini silin ve tekrar calistirin |
| `Redirect URI mismatch` | OAuth istemci turunu "Masaustu uygulamasi" olarak degistirin |
