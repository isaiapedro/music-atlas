"""Apply coarse, wiki-supported regional heartlands to selected genres."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"

# These are intentionally broad display areas, not claimed cultural borders.
REGIONS = {
    "nga-highlife": ["Anambra State", "Delta State", "Imo State", "Rivers State"],
    "mar-gnawa": ["Suss-Massa-Draa", "Marrakesh-Tensift-El Haouz", "Doukkala Abda"],
    "mar-malhun": ["Fès-méknas-boulmane", "Meknès-Tafilalet", "Marrakesh-Tensift-El Haouz"],
    "idn-gamelan": ["West Java", "Central Java", "East Java", "Yogyakarta", "Bali"],
    "bgd-baul-songs": ["Khulna", "Rajshahi"],
    "gha-highlife": ["Central", "Greater Accra", "Western"],
    "gha-adowa": ["Ashanti"],
    "mli-tuareg-guitar": ["Kidal", "Gao", "Tombouctou"],
    "civ-zouglou": ["Lagunes"],
    "bgd-bhatiyali": ["Barisal", "Sylhet", "Chattogram"],
    "pak-mahiya": ["Punjab"],
    "lka-baila": ["Colombo", "Galle", "Kalutara", "Matara"],
    "idn-angklung": ["West Java"],
    "idn-wayang-music": ["Central Java", "Yogyakarta", "East Java", "Bali"],
    "jpn-city-pop": ["Tokyo", "Kanagawa Prefecture", "Chiba Prefecture", "Saitama Prefecture"],
    "eth-zema": ["Amhara", "Tigray"],
    "eth-azmari": ["Amhara"],
    "eth-ethio-jazz": ["Addis Ababa"],
    "tza-taarab": ["Unguja North", "Unguja South", "North Pemba", "South Pemba"],
    "tza-bongo-flava": ["Dar es Salaam", "Pwani"],
    "uga-kadongo-kamu": ["Kampala", "Wakiso", "Mpigi"],
    "dza-ahellil": ["Adrar"],
    "mar-ahwash": ["Suss-Massa-Draa", "Marrakesh-Tensift-El Haouz", "Guelmim-Es Semara"],
    "mar-aita": ["Doukkala Abda", "Chaouia-Ouardigha", "Marrakesh-Tensift-El Haouz"],
    "mar-aissawa": ["Meknès-Tafilalet", "Fès-méknas-boulmane"],
    "egy-semsemiah": ["Port Said", "Ismailia", "Suez"],
    "egy-mahraganat": ["Cairo", "Giza", "Qalyubia"],
    "irn-khorasan-bakhshi": ["North Khorasan"],
    "chn-nanyin": ["Fujian"],
    "chn-shanghai-modern-song": ["Shanghai"],
    "twn-beiguan-music": ["Taipei", "New Taipei", "Taoyuan", "Hsinchu"],
    "gin-sosso-bala": ["Kankan", "Kouroussa Prefecture"],
    "zaf-isicathamiya": ["KwaZulu-Natal"],
    "tjk-falak": ["Gorno-Badakhshan", "Khatlon"],
    "tkm-kushtdepdi": ["Balkan"],
    "afg-kabuli-ghazal": ["Kabul"],
    "mys-mak-yong": ["Kelantan"],
    "mys-joget-gamelan": ["Terengganu", "Pahang"],
    "mng-khoomei": ["Bayan-Ölgii", "Khovd", "Uvs", "Govi-Altai"],
    "mng-tsuur": ["Bayan-Ölgii", "Khovd", "Uvs", "Govi-Altai"],
    "vnm-nha-nhac": ["Thừa Thiên Huế"],
    "vnm-xoan": ["Phú Thọ"],
    "vnm-cheo": ["Red River Delta", "Hanoi", "Thái Bình", "Nam Định"],
    "vnm-central-highlands-gong-culture": ["Gia Lai", "Kon Tum", "Đắk Lắk", "Đắk Nông", "Lâm Đồng"],
    "ago-semba": ["Luanda", "Bengo"],
    "gnq-mvet-oyeng": ["Centro Sur", "Kié-Ntem", "Wele-Nzas"],
    "cmr-mvet-oyeng": ["Centre", "East", "South"],
    "gab-mvet-oyeng": ["Woleu-Ntem", "Ogooué-Ivindo", "Estuaire"],
    "cod-congolese-rumba": ["Kinshasa", "Kongo Central"],
    "cod-musique-moderne-zaireoise": ["Kinshasa"],
    "ken-isukuti-dance": ["Western", "Nyanza"],
    "phl-hudhud-chants": ["Ifugao"],
    "phl-manila-sound-1980s": ["Metro Manila", "Quezon City", "Makati"],
    "lka-nadagam-song": ["Colombo", "Gampaha", "Kalutara", "Puttalam"],
    "nam-aixan-ancestral-music": ["Karas", "Hardap"],
    "phl-kundiman": ["Metro Manila", "Quezon City", "Rizal", "Bulacan"],
    "tcd-ngambaye-vocal-music": ["Logone Occidental", "Logone Oriental", "Mandoul", "Moyen-Chari"],
    "egy-zar": ["Cairo", "Alexandria", "Dakahlia", "Damietta", "Aswan", "Luxor", "Qena", "Sohag"],
    "lby-maluf": ["Tripoli District"],
    "btn-drametse-ngacham": ["Trashigang"],
    "pak-boreendo-music": ["Sindh"],
    "idn-keroncong": ["Jakarta", "Central Java", "Yogyakarta"],
    "afg-naghma-ye-kashal": ["Kabul"],
    "geo-georgian-polyphonic-singing": ["Samegrelo-Zemo Svaneti", "Kakheti", "Guria", "Imereti"],
    "caf-zokela": ["Bangui", "Lobaye Prefecture"],
    "cmr-mendzan-xylophone-traditions": ["Centre", "South"],
    "lao-lam-khap": ["Champasak", "Salavan", "Savannakhet", "Khammouane", "Xiangkhouang"],
    "uzb-yalla-1981-tv-lead": ["Tashkent"],
    "sdn-madih": ["Northern", "River Nile"],
    "psx-zajal": ["West Bank", "Gaza"],
    "irn-persian-pop": ["Tehran", "Alborz"],
    "arm-armenian-folk-ensembles": ["Yerevan"],
    "cog-mvet-oyeng": ["Likouala", "Sangha", "Cuvette"],
    "eri-guayla": ["Maekel", "Debub"],
    # Final country-wide review: sources name a stable city/provincial heartland.
    "irn-radif": ["Isfahan", "Fars", "Qazvin", "Tehran"],
    "gha-hiplife": ["Greater Accra"],
    "ken-gengetone": ["Nairobi"],
    "dza-imzad": ["Tamanghasset", "Illizi"],
    "tur-arabesk": ["Istanbul", "Ankara", "Adana"],
    "tur-anatolian-rock": ["Istanbul"],
    "aze-ashiq": ["Qazax", "Tovuz", "Shamakhi"],
    "zwe-mbende-jerusarema": ["Mashonaland East"],
    "mys-malaysian-popular-music-1950s-1990s": ["Kuala Lumpur"],
    "uzb-shashmaqom": ["Bukhara", "Samarqand"],
    "egy-semsemiah-music": ["Port Said", "Ismailia", "Suez"],
}


def main():
    data = json.loads(CATALOGUE.read_text())
    by_id = {entry["id"]: entry for entry in data["entries"]}
    missing = set(REGIONS) - set(by_id)
    if missing:
        raise ValueError(f"Missing entries: {sorted(missing)}")
    for genre_id, regions in REGIONS.items():
        entry = by_id[genre_id]
        entry["map_scope"] = "regions"
        entry["regions"] = regions
        entry["research"]["geography"] = (
            "Coarse regional heartland derived from reviewed Wikipedia/source wording; "
            "the map is a display aid and does not assert exact cultural boundaries."
        )
    CATALOGUE.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    print(f"applied {len(REGIONS)} regional heartland scopes")


if __name__ == "__main__":
    main()
