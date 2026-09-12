# Tasks: 璁剧疆闈㈡澘涓庛€屾€濊€冨己搴︺€?
## 闃舵 1锛氭暟鎹眰涓?API
- [x] `models.py`锛氭柊澧?`UserSetting(user_id, key, value)`锛屼富閿?`(user_id, key)`锛孎K 绾ц仈鍒犻櫎
- [x] `services/store.py`锛歚get_user_setting` / `set_user_setting`
- [x] `services/user_settings.py`锛氭。浣嶅畾涔変笌鏄犲皠锛?..4 鈫?閫熷害鍊嶇巼锛夈€佽寖鍥存牎楠岋紙0.1~10锛?- [x] `router/settings.py`锛歚GET /api/settings`銆乣PATCH /api/settings`锛堢櫧鍚嶅崟 + 鏍￠獙锛岃秺鐣?400锛?- [x] `main.py` 娉ㄥ唽璺敱
- [x] pytest锛氶粯璁ゅ€煎洖钀姐€佹寜鐢ㄦ埛闅旂銆侀潪娉曞€?400銆佹。浣嶆槧灏?
## 闃舵 2锛氳妭濂忔帴鍏?- [x] `router/chat.py`锛氱敤褰撳墠鐢ㄦ埛鐨?`typing_speed` 瑕嗙洊 `settings.typing_speed`锛坄dataclasses.replace`锛?- [x] 淇濇寔 `typing_speed <= 0` 鐨勬棦鏈夈€屼笉鑺傛祦銆嶈涔変笉鍙?- [x] pytest锛氳缃簡閫熷害鍚庯紝chat 鐢熸晥锛涙湭璁剧疆鏃跺洖钀界幆澧冨彉閲忥紱杩涜涓殑娴佷笉鍙楀悗缁敼鍔ㄥ奖鍝?
## 闃舵 3锛氬墠绔缃潰鏉?- [x] 鏂板 `components/SettingsDialog.tsx`锛坄role="dialog"` + `aria-modal` + Esc + 鐒︾偣闄烽槺 + 鐒︾偣鍥炲綊锛?- [x] 鍐呴儴鍖呭惈锛氭€濊€冨己搴︽粦鏉嗭紙4 妗?+ 妗ｄ綅鍚?+ 璇存槑锛夈€佹繁鑹蹭富棰樸€佸鏉炬帓鐗堛€佸揩閫熼槄璇汇€侀€€鍑虹櫥褰?- [x] `Sidebar`锛氬簳閮ㄦ敼涓?杩涘害 + 銆岃缃€嶆寜閽?+ 鐢ㄦ埛鍖猴紱绉婚櫎鍘熸潵鐨勫洓涓紑鍏充笌閫€鍑烘寜閽?- [x] `App.tsx`锛歚settingsOpen` 鐘舵€侊紱鎷夊彇/淇濆瓨鐢ㄦ埛璁剧疆锛涙妸鎬濊€冨己搴︿紶缁欏悗绔?- [x] 鏍峰紡锛氶潰鏉夸笌鏃㈡湁 `UserAdminDialog` 澶嶇敤鍚屼竴濂?modal 鏍峰紡

## 闃舵 4锛氬彲娴嬭瘯鎬?- [x] 鏂板 `data-testid`锛歚settings-button` / `settings-dialog` / `settings-close` / `thinking-slider` / `thinking-label`
- [x] **淇濇寔涓嶅彉**鐨?testid锛歚theme-toggle` / `reading-mode-toggle` / `quick-read-toggle` / `logout-button`锛堝彧鏄崲浜嗕綅缃級
- [x] 鏇存柊鏃㈡湁 E2E锛氬厛鎵撳紑璁剧疆闈㈡澘鍐嶇偣杩欎簺寮€鍏筹紙`ui-shell.spec.ts` 鐨勪富棰?闃呰瀹藉害鐢ㄤ緥銆乣accounts.spec.ts` 鐨勯€€鍑虹櫥褰曠敤渚嬶級

## 闃舵 5锛氭祴璇?- [x] 鏂板 E2E锛氭墦寮€/鍏抽棴璁剧疆闈㈡澘銆佺劍鐐瑰洖褰?- [x] 鏂板 E2E锛氫晶鏍忓凡涓嶅惈鍥涗釜寮€鍏筹紱璁剧疆闈㈡澘鍐呭惈瀹冧滑
- [x] 鏂板 E2E锛氭€濊€冨己搴﹀垏妗ｅ悗**鍒锋柊浠嶄繚鎸?*锛堟寜鐢ㄦ埛淇濆瓨锛?- [x] 鏂板 E2E锛氭妸寮哄害璋冨埌銆屾矇鎬濄€嶏紝鏂█鍑哄瓧鑺傚姣斻€岃繀鎹枫€嶆參锛堜互銆屾敹灏惧嚭鐜版墍闇€鏃堕棿銆嶄负鍙娴嬮噺锛?- [x] 鍏ㄩ噺閫氳繃锛坧ytest / vitest / Playwright锛?
## 闃舵 6锛氶儴缃蹭笌楠岃瘉
- [x] 鏈湴鏋勫缓 + 鍏ㄩ噺娴嬭瘯
- [x] 閮ㄧ讲鍒?192.168.178.116锛屽绾夸笂璺戝叏閲?E2E
- [x] 鐩鏍稿锛氫晶鏍忕簿绠€鍚庣殑鏍峰瓙銆佽缃潰鏉裤€佹粦鏉嗘墜鎰?- [x] 鎻愪氦鎺ㄩ€侊紱`openspec archive settings-panel`