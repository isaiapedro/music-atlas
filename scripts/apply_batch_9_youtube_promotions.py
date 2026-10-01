import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE = ROOT / "research" / "genre_catalogue.json"
PROMOTIONS = {
 "sol-heello-hees-hargeysa": ("Brothers of Hargeysa (Walaalo Hargeysa)", "Balooy Baydh | Walaalaha Hargeysa", "WmWVcXU7t7g"),
 "tha-lam-isan": ("Mor Lam performers", "Mor Lam is a traditional folk performing art of the Isan people", "9IjbLvpW_AY"),
 "tza-singeli": ("AY Masta", "Singeli Twista", "Ua4PHA6tbEU"),
 "uga-kadongo-kamu": ("Kadongo Kamu Music Classics", "Kadongo Kamu Nonstop Mix", "Kvlg06oq0YA"),
 "uga-kidandali": ("Ziza Bafana", "Kidandali", "KQ1qs35iNZI"),
}
def main():
 data=json.loads(CATALOGUE.read_text()); found=set()
 for e in data["entries"]:
  if e["id"] not in PROMOTIONS: continue
  artist,title,vid=PROMOTIONS[e["id"]]
  if artist not in e["artists"]: e["artists"].append(artist)
  e["youtube_examples"]=[{"artist":artist,"title":title,"youtube_url":f"https://www.youtube.com/watch?v={vid}","reviewed_at":"2026-09-28"}]
  e["research"]["sample"]="Reviewed direct YouTube example; attribution basis is recorded in Batch 9 search log."; found.add(e["id"])
 CATALOGUE.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n"); print(f"promoted {len(found)} Batch 9 YouTube examples")
if __name__=="__main__": main()
