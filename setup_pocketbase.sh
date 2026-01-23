#!/bin/bash

# Renkli çıktılar için
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== PocketBase Kurulum Scripti ===${NC}"

# 1. PocketBase kontrolü ve indirme
if [ ! -f "pocketbase" ]; then
    echo -e "${BLUE}PocketBase bulunamadı. İndiriliyor...${NC}"
    # v0.22.4 Linux AMD64
    wget https://github.com/pocketbase/pocketbase/releases/download/v0.22.4/pocketbase_0.22.4_linux_amd64.zip -O pocketbase.zip

    if [ $? -ne 0 ]; then
        echo -e "${RED}İndirme başarısız oldu.${NC}"
        exit 1
    fi

    echo -e "${BLUE}Zipli dosya açılıyor...${NC}"
    unzip -o pocketbase.zip
    rm pocketbase.zip
    chmod +x pocketbase
    echo -e "${GREEN}PocketBase indirildi ve kuruldu.${NC}"
else
    echo -e "${GREEN}PocketBase zaten mevcut.${NC}"
fi

# Yönetici bilgileri
ADMIN_EMAIL="admin@local.host"
ADMIN_PASS="password123456"

# 2. Yönetici hesabı oluşturma (eğer pb_data yoksa)
if [ ! -d "pb_data" ]; then
    echo -e "${BLUE}İlk kurulum: Veritabanı başlatılıyor ve yönetici hesabı oluşturuluyor...${NC}"

    # Migrations uygula (pb_migrations klasöründeki dosyalar otomatik işlenir)
    ./pocketbase migrate up

    # Yönetici hesabı oluştur
    ./pocketbase admin create "$ADMIN_EMAIL" "$ADMIN_PASS"

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Başlangıç kurulumu tamamlandı.${NC}"
    else
        echo -e "${RED}Kurulum sırasında bir hata oluştu.${NC}"
    fi
else
    echo -e "${BLUE}Mevcut veri klasörü bulundu (pb_data). Kurulum adımları atlanıyor.${NC}"
fi

echo -e ""
echo -e "${GREEN}===========================================${NC}"
echo -e "${GREEN}KURULUM BAŞARIYLA TAMAMLANDI!${NC}"
echo -e "${GREEN}===========================================${NC}"
echo -e "PocketBase'i başlatmak için: ${BLUE}./pocketbase serve${NC}"
echo -e "Admin Paneli: ${BLUE}http://127.0.0.1:8090/_/${NC}"
echo -e "Giriş Bilgileri (Yeni kurulduysa):"
echo -e "Email: ${BLUE}$ADMIN_EMAIL${NC}"
echo -e "Şifre: ${BLUE}$ADMIN_PASS${NC}"
