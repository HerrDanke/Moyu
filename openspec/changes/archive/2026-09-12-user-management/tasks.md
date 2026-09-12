# Tasks: 鐢ㄦ埛绠＄悊

## 闃舵 0锛氬噯澶囦笌杩佺Щ璁捐
- [x] 纭 `ACCESS_PASSWORD` 閫€褰硅矾寰勶紙compose / .env.example / README锛?- [x] 鍐欒縼绉绘帰娴嬶細`progress` 鏄惁宸叉湁 `user_id` 鍒楋紱鏃犲垯閲嶅懡鍚嶄负 `progress_legacy`

## 闃舵 1锛氭暟鎹眰
- [x] `models.py`锛氭柊澧?`User`锛沗progress` 鏀逛负涓婚敭 `(user_id, book_id)`锛沗books` 鍔?`uploaded_by`锛沗settings` 绉婚櫎 current_book 璇箟
- [x] `db.py`锛氬惎鍔ㄨ縼绉诲嚱鏁帮紙閲嶅懡鍚?legacy 琛?+ create_all + 骞傜瓑锛?- [x] `security.py`锛歚hash_password` / `verify_password`锛坰crypt 浼樺厛锛宲bkdf2 鍥為€€锛沗hmac.compare_digest`锛?- [x] pytest锛氬搱甯屽線杩斻€侀敊璇瘑鐮併€佺洂鍞竴鎬с€佽縼绉诲箓绛?
## 闃舵 2锛氶壌鏉冧笌浼氳瘽
- [x] `security.py`锛歋ession 杞借嵎鏀逛负鎼哄甫 `user_id` **涓?`token_version`**锛堝惈绛惧彂/瑙ｆ瀽锛?- [x] `security.py`锛歚hash_password` 澶栧眰鍔?*鍏ㄥ眬骞跺彂淇″彿閲?*锛堟渶澶?2 涓?KDF 骞惰锛夛紱鐢ㄦ埛涓嶅瓨鍦ㄦ椂璺?dummy 鍝堝笇锛屾姽骞宠鏃跺樊
- [x] `deps.py`锛歚get_current_user`锛堟煡搴撴牎楠屽瓨鍦ㄣ€佸惎鐢ㄣ€乣token_version` 涓€鑷达級銆乣require_admin`
- [x] `deps.py`锛氭棤鐢ㄦ埛锛坄setup_required`锛夋椂闄?login/status/setup 澶栧叏閮?401
- [x] `router/auth.py`锛歚login(username,password)` / `logout` / `me` / `status(setup_required)`
- [x] 鐧诲綍闄愰€燂細閿负 `(IP, username)` 鐨勯€€閬胯妭娴?+ 鍏ㄥ眬浠ょ墝妗讹紱涓嶇‖閿?- [x] 瀵嗙爜瀛楁鍔?`max_length`
- [x] **淇鍚姩瀹堝崼**锛歚_assert_secure_config` 鏀逛负銆屽瓨鍦ㄤ换鎰忕敤鎴?+ 绌?寮?SECRET_KEY 鈫?鎷掔粷鍚姩銆嶏紙鍘熸潯浠朵緷璧?ACCESS_PASSWORD锛岄€€褰瑰悗浼氭亽涓哄亣锛屽鑷村彲鐢ㄩ粯璁ゅ瘑閽ヨ嚜绛?Cookie 缁曡繃閴存潈锛?- [x] pytest锛氱櫥褰曟垚鍔?澶辫触銆佸仠鐢ㄧ敤鎴疯鎷掋€佹棫鐗堟棤 user_id Cookie 琚嫆銆佹敼瀵嗗悗鏃т細璇濆け鏁堛€侀檺閫熺敓鏁堛€佹棤鐢ㄦ埛鏃跺叏绔?401銆佸急瀵嗛挜鎷掔粷鍚姩

## 闃舵 3锛氶娆¤繍琛屽紩瀵?- [x] 鍚姩鏃惰嫢鏃犵敤鎴峰垯鐢?`secrets` 鐢熸垚涓€娆℃€у紩瀵煎彛浠ゅ苟鎵撳嵃鍒版棩蹇?- [x] `POST /api/auth/setup`锛?*鍏堟牎楠屽彛浠わ紙`compare_digest`锛夊啀鎵ц KDF**锛涙棤鐢ㄦ埛 + 瀵嗙爜闀垮害 鈮? + 鐢ㄦ埛鍚嶆牸寮?- [x] 寮曞鎺ュ彛鍚屾牱鍙楅檺閫熺害鏉燂紱`/api/auth/status` 涓嶈繑鍥炲彛浠?- [x] 鍒涘缓鎴愬姛鍚庯細鍥炲～ `progress_legacy` 鍒拌绠＄悊鍛樸€佽縼绉?`settings.current_book`銆佷綔搴熷彛浠ゃ€佸叧闂帴鍙?- [x] pytest锛氬彛浠ら敊璇鎷掞紙涓旀湭瑙﹀彂 KDF锛夈€佹垚鍔熷悗鎺ュ彛鍏抽棴銆佽€佹暟鎹綊灞炵鐞嗗憳

## 闃舵 4锛氱敤鎴风鐞?API
- [x] `router/users.py`锛氬垪琛?/ 鍒涘缓 / 閲嶇疆瀵嗙爜 / 鍒囨崲绠＄悊鍛?/ 鍋滅敤 / 鍒犻櫎
- [x] 淇濇姢瑙勫垯锛氫笉鑳藉垹闄ゆ垨鍋滅敤鑷繁锛涗笉鑳藉垹闄?闄嶇骇/鍋滅敤**鏈€鍚庝竴涓惎鐢ㄧ殑绠＄悊鍛?*锛涚敤鎴峰悕鍞竴锛?09锛?- [x] 閲嶇疆瀵嗙爜 / 鍋滅敤 / 鍒犻櫎鏃惰嚜澧?`token_version`锛堝悐閿€鍏朵細璇濓級
- [x] 鏇存柊鎺ュ彛浣跨敤瀛楁鐧藉悕鍗曪紝闃茶秺鏉冩敼 `is_admin`
- [x] pytest锛氶潪绠＄悊鍛?403銆侀噸鍚?409銆佹渶鍚庣鐞嗗憳淇濇姢銆佽嚜鎴戦攣姝讳繚鎶ゃ€佸垹闄ょ敤鎴锋竻杩涘害銆佹敼瀵嗗悐閿€浼氳瘽

## 闃舵 5锛氳繘搴︿笌涔︾睄鎸夌敤鎴烽殧绂?- [x] `services/store.py`锛歚get_current_book`锛?*鍚寜 `updated_at` 鍏ㄥ簱鎺掑簭鐨勫洖閫€鍒嗘敮**锛変笌 `write_progress` 鍏ㄩ儴甯?`user_id`
- [x] `router/progress.py`锛氳鍐欏綋鍓嶇敤鎴疯繘搴︼紙`session.get(Progress, (user_id, book_id))`锛?- [x] `router/chat.py` + `services/chat_engine.py`锛氳繘搴︿笌褰撳墠涔︾粦瀹氬綋鍓嶇敤鎴?- [x] `router/books.py`锛氫功鍗曞叡浜?+ 杩斿洖瀵煎叆鑰呭悕锛涘垹闄や功闇€绠＄悊鍛樺苟娓呮墍鏈夌敤鎴疯繘搴︼紱select 鍙敼鏈汉
- [x] pytest锛氫袱鐢ㄦ埛鍚屼功杩涘害浜掍笉褰卞搷锛汚 涓嶈兘璇诲埌/鍐欏埌 B 鐨勮繘搴︼紱B 鐨勫綋鍓嶄功涓嶇户鎵?A 鐨勬渶杩戦槄璇?
## 闃舵 6锛氬墠绔?- [x] `LoginPage`锛氱敤鎴峰悕 + 瀵嗙爜 + 閿欒鎻愮ず
- [x] `SetupPage`锛堟柊澧烇級锛氱敤鎴峰悕 + 瀵嗙爜 + 寮曞鍙ｄ护
- [x] `App.tsx`锛歚setup_required` 鍒嗘敮銆佸綋鍓嶇敤鎴风姸鎬併€乣/api/auth/me` 鎷夊彇
- [x] `Sidebar`锛氱敤鎴峰尯锛堢敤鎴峰悕 + 韬唤 + 閫€鍑猴級銆佺鐞嗗憳銆岀敤鎴风鐞嗐€嶅叆鍙?- [x] `UserAdminDialog`锛堟柊澧烇級锛氬垪琛?/ 鏂板缓 / 閲嶇疆瀵嗙爜 / 鍒囨崲绠＄悊鍛?/ 鍒犻櫎锛堜簩娆＄‘璁わ級銆丒sc 鍏抽棴 + 鐒︾偣鍥炲綊
- [x] 鍝佺墝锛氭柊澧?`Logo.tsx`锛堝師鍒?SVG 鏍囪锛? 渚ф爮 wordmark銆屽ⅷ楸笺€?- [x] 鍏ㄩ儴浜や簰鍏冪礌琛?`data-testid`

## 闃舵 7锛氭祴璇?- [x] 鏇存柊鏃㈡湁 E2E锛氱櫥褰曡緟鍔╁嚱鏁版敼涓恒€岄娆″紩瀵煎缓鍙?/ 宸插缓鍙峰垯鐧诲綍銆?- [x] 鏂板 E2E锛氶娆″紩瀵奸〉鍑虹幇涓旈敊璇彛浠よ鎷?- [x] 鏂板 E2E锛氱鐞嗗憳鍒涘缓鐢ㄦ埛 鈫?鏂扮敤鎴风櫥褰?鈫?涓や汉璇诲悓涓€鏈功杩涘害浜掍笉骞叉壈
- [x] 鏂板 E2E锛氭櫘閫氱敤鎴风湅涓嶅埌銆岀敤鎴风鐞嗐€嶅叆鍙?- [x] 鏂板 E2E锛氬搧鐗屾爣璇嗗尯涓嶅寘鍚?ChatGPT/OpenAI 鏂囨
- [x] 鍏ㄩ噺閫氳繃锛坧ytest / vitest / Playwright锛?
## 闃舵 8锛氶儴缃蹭笌楠岃瘉
- [x] `docker-compose.yml`锛氬幓鎺?`ACCESS_PASSWORD` 寮哄埗椤癸紱`.env.example` / README 鏇存柊鍗囩骇璇存槑
- [x] 鏈湴鏋勫缓 + 鍏ㄩ噺娴嬭瘯
- [x] 閮ㄧ讲鍒?192.168.178.116锛氶獙璇佸瓨閲忋€婂疇榄呫€嬩笌杩涘害杩佺Щ鍒伴涓鐞嗗憳
- [x] 绾夸笂璺戝叏閲?E2E锛涚洰瑙嗘牳瀵圭櫥褰曢〉 / 鑷姩寮曞 / 鐢ㄦ埛绠＄悊 / 鍝佺墝鏍囪瘑
- [x] 鎻愪氦鎺ㄩ€侊紱`openspec archive user-management`