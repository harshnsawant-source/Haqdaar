# Translation review sheet

**Status: REVIEWED 2026-09-02.** Confirmed complete by Harsh, who is a Marathi and
Hindi speaker. Every section below has been read against its source file.

Marathi and Hindi were drafted in one pass on 2026-08-26 and this sheet was written to
get them checked by a native speaker. That check has now happened, so the strings that
ship are human-reviewed rather than unreviewed machine output. If a string is edited
after this date, untick its section and read it again: the whole point of the sheet is
that nobody has to take the translation on trust.

## Why this is not cosmetic

A mistranslated eligibility rule sends a real person to a government office to be
turned away. A mistranslated *question* is worse, because it changes what she
answers, which changes her profile, which changes her verdict, and nothing on screen
will look wrong.

Two questions carry an official carve-out for Multi Tasking Staff, Class IV and
Group D employees. If a translation drops that clause, the system silently
disqualifies the lowest-paid government workers in the country. Check those two
first: `government_employee` and `monthly_pension`.

## Rules a fix must not break

1. **Keep every `{slot}` exactly as written.** They are filled with real values at
   render time. A dropped slot renders a sentence with its number missing.
2. **No digits, in any script.** Devanagari numerals (० १ २) fail the build audit
   exactly like ASCII ones. Numbers arrive through slots, never in the prose.
3. **Do not soften a refusal.** Several lines are deliberately blunt. "I will not
   guess" must not become "maybe".
4. Run `./.venv/Scripts/python.exe -m pytest engine/tests -q` after editing. The
   structural rules above are all enforced.

## Verdict templates

Source: `engine/haqdaar/render/templates/mr.yaml` and `hi.yaml`

- [x] Marathi reviewed
- [x] Hindi reviewed

| Key | English | Marathi | Hindi |
|---|---|---|---|
| `eligible.headline` | You are eligible for {scheme_name}. | तुम्ही {scheme_name} साठी पात्र आहात. | आप {scheme_name} के लिए पात्र हैं. |
| `eligible.proof_intro` | Here is the rule that entitles you: | तुम्हाला हा हक्क देणारा नियम असा आहे: | यह रहा वह नियम जो आपको यह हक देता है: |
| `eligible.proof_line` | {clause_text} | {clause_text} | {clause_text} |
| `eligible.proof_source` | Source: {source_url} | स्रोत: {source_url} | स्रोत: {source_url} |
| `eligible.evidence_line` | Proven from your {document}. | तुमच्या {document} वरून हे सिद्ध झाले. | आपके {document} से यह प्रमाणित हुआ. |
| `eligible.next_step` | Apply at {filing_office}. | {filing_office} येथे अर्ज करा. | {filing_office} पर आवेदन करें. |
| `not_eligible.headline` | Not this one, and here is exactly why. | ही योजना तुमच्यासाठी नाही, आणि त्याचे नेमके कारण असे आहे. | यह योजना आपके लिए नहीं है, और इसका सटीक कारण यह है. |
| `not_eligible.reason` | The rule says {bound_text}. Your {field_label} is {value}. | नियम सांगतो {bound_text}. तुमचे {field_label} आहे {value}. | नियम कहता है {bound_text}. आपका {field_label} है {value}. |
| `not_eligible.reason_required` | This one requires {field_label}. You told me {value}. | यासाठी {field_label} आवश्यक आहे. तुम्ही सांगितले {value}. | इसके लिए {field_label} आवश्यक है. आपने बताया {value}. |
| `not_eligible.reason_excluded` | This one rules out {field_label}. You told me {value}. | {field_label} असल्यास ही योजना मिळत नाही. तुम्ही सांगितले {value}. | {field_label} होने पर यह योजना नहीं मिलती. आपने बताया {value}. |
| `not_eligible.becomes_eligible` | You become eligible in {year}. | {year} साली तुम्ही पात्र व्हाल. | {year} में आप पात्र हो जाएंगे. |
| `blocked.headline` | You are one document away. | फक्त एक कागदपत्र कमी आहे. | बस एक दस्तावेज़ की कमी है. |
| `blocked.single` | Bring your {document} and this unlocks {scheme_name}. | तुमचा {document} आणा, त्यामुळे {scheme_name} मिळू शकेल. | अपना {document} लाइए, इससे {scheme_name} मिल सकेगी. |
| `blocked.multiple` | Bring your {document} and this unlocks {count} more schemes. | तुमचा {document} आणा, त्यामुळे आणखी {count} योजना मिळू शकतील. | अपना {document} लाइए, इससे {count} और योजनाएं मिल सकेंगी. |
| `blocked.where` | You can get it from {office}. | तो तुम्हाला {office} येथून मिळेल. | यह आपको {office} से मिलेगा. |
| `blocked.rule` | The rule this settles: {clause_text} | हा नियम त्यामुळे पूर्ण होतो: {clause_text} | इससे यह नियम पूरा होता है: {clause_text} |
| `unverifiable.headline` | I cannot confirm this one, and I will not guess. | याची खात्री मी करू शकत नाही, आणि मी अंदाज लावणार नाही. | इसकी पुष्टि मैं नहीं कर सकता, और मैं अंदाज़ा नहीं लगाऊंगा. |
| `unverifiable.reason_dataset` | This scheme's rule depends on records I cannot check, and nothing you have shown me can prove it. | या योजनेचा नियम अशा नोंदींवर अवलंबून आहे ज्या मी तपासू शकत नाही, आणि तुम्ही दाखवलेल्या कोणत्याही कागदपत्रावरून तो सिद्ध होत नाही. | इस योजना का नियम ऐसे अभिलेखों पर निर्भर है जिन्हें मैं जांच नहीं सकता, और आपने जो दिखाया है उससे वह प्रमाणित नहीं होता. |
| `unverifiable.reason_discretionary` | That is decided by {decider}, not by any document. | तो निर्णय {decider} घेतात, कोणतेही कागदपत्र नाही. | वह निर्णय {decider} लेते हैं, कोई दस्तावेज़ नहीं. |
| `unverifiable.rule` | The rule I cannot settle: {clause_text} | जो नियम मी ठरवू शकत नाही: {clause_text} | जो नियम मैं तय नहीं कर सकता: {clause_text} |
| `unverifiable.also_unsettleable` | The same records settle {count} further criteria in this scheme, and I cannot check any of them. | याच नोंदींवर या योजनेतील आणखी {count} अटी अवलंबून आहेत, आणि त्यांपैकी एकही मी तपासू शकत नाही. | इन्हीं अभिलेखों पर इस योजना की {count} और शर्तें निर्भर हैं, और उनमें से किसी को भी मैं जांच नहीं सकता. |
| `unverifiable.next_step` | Ask at {office} and quote that rule. | {office} येथे विचारा आणि तोच नियम सांगा. | {office} पर पूछिए और वही नियम बताइए. |
| `unverifiable.promise` | If they confirm it, come back and I will complete your application. | त्यांनी खात्री दिली तर परत या, मी तुमचा अर्ज पूर्ण करेन. | यदि वे पुष्टि कर दें तो लौट आइए, मैं आपका आवेदन पूरा कर दूंगा. |
| `unverifiable.outside_corpus` | That is outside what I have rules for. I only answer where I can show you the official clause. | त्याबाबतचे नियम माझ्याकडे नाहीत. जिथे मी तुम्हाला अधिकृत तरतूद दाखवू शकतो तिथेच मी उत्तर देतो. | उसके नियम मेरे पास नहीं हैं. मैं वहीं उत्तर देता हूं जहां आपको आधिकारिक प्रावधान दिखा सकूं. |
| `window.lapsed_headline` | Stop. The period this scheme was sanctioned for has ended. | थांबा. या योजनेला मंजूर असलेला कालावधी संपला आहे. | रुकिए. इस योजना के लिए स्वीकृत अवधि समाप्त हो चुकी है. |
| `window.lapsed_reason` | The rules I have run until {valid_until}. | माझ्याकडील नियम {valid_until} पर्यंतचे आहेत. | मेरे पास के नियम {valid_until} तक के हैं. |
| `window.lapsed_source` | The official document says: {validity_text} | अधिकृत कागदपत्रात असे म्हटले आहे: {validity_text} | आधिकारिक दस्तावेज़ में लिखा है: {validity_text} |
| `window.lapsed_proof_kept` | I have still checked you against its published rules below. Confirm at the office whether a successor has taken its place before you spend a day on this. | तरीही मी तुम्हाला या योजनेच्या जाहीर नियमांनुसार खाली तपासले आहे. यावर वेळ घालवण्यापूर्वी तिच्या जागी नवी योजना आली आहे का, हे कार्यालयात विचारून घ्या. | फिर भी मैंने आपको इसके प्रकाशित नियमों के अनुसार नीचे जांचा है. इस पर समय लगाने से पहले कार्यालय में पूछ लें कि इसकी जगह कोई नई योजना आई है या नहीं. |
| `window.not_yet_open_headline` | This scheme has not opened yet. | ही योजना अद्याप सुरू झालेली नाही. | यह योजना अभी शुरू नहीं हुई है. |
| `window.not_yet_open_reason` | It opens on {valid_from}. | ती {valid_from} रोजी सुरू होते. | यह {valid_from} को शुरू होती है. |
| `approval.headline` | Whether it is approved is not mine to promise. | मंजुरी मिळेल का, याचे वचन देणे माझ्या हातात नाही. | मंजूरी मिलेगी या नहीं, इसका वादा करना मेरे हाथ में नहीं है. |
| `approval.refusal` | That is decided by {decider}, and no document you hold determines it. | तो निर्णय {decider} घेतात, आणि तुमच्याकडील कोणतेही कागदपत्र तो ठरवत नाही. | वह निर्णय {decider} लेते हैं, और आपके पास का कोई दस्तावेज़ उसे तय नहीं करता. |
| `approval.rule` | The condition: {clause_text} | अट अशी आहे: {clause_text} | शर्त यह है: {clause_text} |
| `staleness.banner` | This rule was last checked on {retrieved_on}. Confirm it is current before you rely on it. | हा नियम शेवटचा {retrieved_on} रोजी तपासला होता. त्यावर अवलंबून राहण्यापूर्वी तो आजही लागू आहे का, याची खात्री करा. | यह नियम अंतिम बार {retrieved_on} को जांचा गया था. इस पर भरोसा करने से पहले पुष्टि कर लें कि यह आज भी लागू है. |
| `staleness.amended` | The source records a change on {last_amended}, after I read it. | मी वाचल्यानंतर {last_amended} रोजी स्रोतामध्ये बदल नोंदवला गेला आहे. | मेरे पढ़ने के बाद {last_amended} को स्रोत में बदलाव दर्ज हुआ है. |
| `source.checked` | Checked against the official source on {retrieved_on}. | अधिकृत स्रोताशी {retrieved_on} रोजी पडताळून पाहिले. | आधिकारिक स्रोत से {retrieved_on} को मिलान किया गया. |
| `provisional.banner` | This rule has not yet been verified against the official source. It is not safe to act on. | हा नियम अद्याप अधिकृत स्रोताशी पडताळलेला नाही. त्यावर कृती करणे सुरक्षित नाही. | यह नियम अभी तक आधिकारिक स्रोत से सत्यापित नहीं है. इस पर कार्रवाई करना सुरक्षित नहीं है. |
| `intake.declared_banner` | This is based on what you told me. I have not seen your documents, so anything that needs a certificate is still marked as needing one. | हे तुम्ही मला जे सांगितले त्यावर आधारित आहे. मी तुमची कागदपत्रे पाहिलेली नाहीत, त्यामुळे ज्यासाठी दाखला लागतो ते अजूनही बाकी म्हणून दाखवले आहे. | यह उस पर आधारित है जो आपने मुझे बताया. मैंने आपके दस्तावेज़ नहीं देखे हैं, इसलिए जिनके लिए प्रमाणपत्र चाहिए वे अब भी बाकी दिखाए गए हैं. |
| `action.headline` | I have filled what your documents can prove for {scheme_name}. | {scheme_name} साठी तुमच्या कागदपत्रांवरून जे सिद्ध होते ते मी भरले आहे. | {scheme_name} के लिए आपके दस्तावेज़ों से जो प्रमाणित होता है, वह मैंने भर दिया है. |
| `action.simulated_banner` | SIMULATED. Nothing has been submitted to any government portal, and this reference is generated on this device. It is not an application. | ही केवळ नक्कल आहे. कोणत्याही सरकारी संकेतस्थळावर काहीही पाठवलेले नाही, आणि हा संदर्भ क्रमांक याच उपकरणावर तयार झाला आहे. हा अर्ज नाही. | यह केवल नकल है. किसी सरकारी पोर्टल पर कुछ भी नहीं भेजा गया है, और यह संदर्भ संख्या इसी डिवाइस पर बनी है. यह आवेदन नहीं है. |
| `action.stand_in_banner` | SIMULATED FORM LAYOUT. This is a stand-in we built, not the official application document. | ही केवळ नक्कल असलेली अर्जाची रचना आहे. हा आम्ही तयार केलेला नमुना आहे, अधिकृत अर्ज नाही. | यह केवल नकल वाला फ़ॉर्म प्रारूप है. यह हमारा बनाया नमूना है, आधिकारिक आवेदन दस्तावेज़ नहीं. |
| `action.filled_count` | Filled {count} fields from your documents. | तुमच्या कागदपत्रांवरून {count} रकाने भरले. | आपके दस्तावेज़ों से {count} खाने भरे. |
| `action.gap_intro` | You still need to supply these: | हे अजून तुम्हाला द्यावे लागेल: | ये अब भी आपको देने होंगे: |
| `action.gap_line` | {label} | {label} | {label} |
| `action.gap_document` | Bring your {document} — it supplies {count} of them. | तुमचा {document} आणा, त्यातून यांपैकी {count} मिळतील. | अपना {document} लाइए, उससे इनमें से {count} मिल जाएंगे. |
| `action.complete` | Nothing is missing from what this form asks for. | हा अर्ज जे मागतो त्यातले काहीही बाकी नाही. | यह फ़ॉर्म जो मांगता है उसमें कुछ भी बाकी नहीं है. |
| `action.tracking` | Your simulated reference: {reference} | तुमचा नक्कल संदर्भ क्रमांक: {reference} | आपकी नकल संदर्भ संख्या: {reference} |
| `action.approval_pending` | Filing does not mean approval. That is still decided by {decider}. | अर्ज दाखल करणे म्हणजे मंजुरी नव्हे. तो निर्णय {decider} घेतात. | आवेदन दाखिल करने का अर्थ मंजूरी नहीं है. वह निर्णय {decider} ही लेते हैं. |

## Intake: needs, questions and options

Source: `corpus/intake.yaml`

- [x] Marathi reviewed
- [x] Hindi reviewed

| Where | English | Marathi | Hindi |
|---|---|---|---|
| need `start-a-business` | I want to start or grow a business | मला व्यवसाय सुरू करायचा आहे किंवा वाढवायचा आहे | मैं व्यवसाय शुरू करना या बढ़ाना चाहता हूं |
| need `business-capital` | I need money or a loan for my work | माझ्या कामासाठी मला पैसे किंवा कर्ज हवे आहे | मुझे अपने काम के लिए पैसे या कर्ज़ चाहिए |
| need `widowed` | My husband has died and I have no income | माझे पती वारले आहेत आणि माझ्याकडे उत्पन्न नाही | मेरे पति का निधन हो गया है और मेरी कोई आय नहीं है |
| need `farm-support` | I farm my own land and need support | मी माझ्या स्वतःच्या जमिनीत शेती करतो आणि मला मदत हवी आहे | मैं अपनी ज़मीन पर खेती करता हूं और मुझे सहायता चाहिए |
| need `old-age-or-health` | I am older, or I need help with medical costs | माझे वय झाले आहे, किंवा मला वैद्यकीय खर्चासाठी मदत हवी आहे | मेरी उम्र हो गई है, या मुझे इलाज के खर्च में मदद चाहिए |
| need `school-fees` | I am at school and my family cannot afford the costs | मी शाळेत आहे आणि माझ्या कुटुंबाला खर्च परवडत नाही | मैं स्कूल में हूं और मेरा परिवार खर्च नहीं उठा सकता |
| need `college-fees` | I have a college place and need help paying for it | मला महाविद्यालयात प्रवेश मिळाला आहे आणि फी भरण्यासाठी मदत हवी आहे | मुझे कॉलेज में दाखिला मिला है और फीस भरने में मदद चाहिए |
| section `about-you` | About you | तुमच्याबद्दल | आपके बारे में |
| Q `age` | How old are you? | तुमचे वय किती आहे? | आपकी उम्र कितनी है? |
| Q `gender` | What is your gender? | तुमचे लिंग काय आहे? | आपका लिंग क्या है? |
| &nbsp;&nbsp;opt `FEMALE` | Woman | स्त्री | महिला |
| &nbsp;&nbsp;opt `MALE` | Man | पुरुष | पुरुष |
| &nbsp;&nbsp;opt `TRANSGENDER` | Transgender | तृतीयपंथी | ट्रांसजेंडर |
| Q `marital_status` | What is your marital status? | तुमची वैवाहिक स्थिती काय आहे? | आपकी वैवाहिक स्थिति क्या है? |
| &nbsp;&nbsp;opt `WIDOW` | Widowed | विधवा | विधवा |
| &nbsp;&nbsp;opt `DIVORCED` | Divorced | घटस्फोटित | तलाकशुदा |
| &nbsp;&nbsp;opt `MARRIED` | Married | विवाहित | विवाहित |
| &nbsp;&nbsp;opt `UNMARRIED` | Unmarried | अविवाहित | अविवाहित |
| Q `social_category` | What is your social category? | तुमचा सामाजिक प्रवर्ग कोणता आहे? | आपका सामाजिक वर्ग कौन सा है? |
| &nbsp;&nbsp;opt `SC` | Scheduled Caste | अनुसूचित जाती | अनुसूचित जाति |
| &nbsp;&nbsp;opt `ST` | Scheduled Tribe | अनुसूचित जमाती | अनुसूचित जनजाति |
| &nbsp;&nbsp;opt `OBC` | OBC | इतर मागास प्रवर्ग | अन्य पिछड़ा वर्ग |
| &nbsp;&nbsp;opt `GENERAL` | General | खुला प्रवर्ग | सामान्य वर्ग |
| section `household` | Your household | तुमचे कुटुंब | आपका परिवार |
| Q `landholding` | How much cultivable land is in your name, in hectares? | तुमच्या नावावर किती लागवडीयोग्य जमीन आहे, हेक्टरमध्ये? | आपके नाम पर कितनी कृषि योग्य भूमि है, हेक्टेयर में? |
| Q `annual_income` | What is your family's total income for a year, in rupees? | तुमच्या कुटुंबाचे वार्षिक एकूण उत्पन्न किती आहे, रुपयांमध्ये? | आपके परिवार की वार्षिक कुल आय कितनी है, रुपयों में? |
| Q `bpl` | Is your family on the Below Poverty Line list? | तुमचे कुटुंब दारिद्र्यरेषेखालील यादीत आहे का? | क्या आपका परिवार गरीबी रेखा से नीचे की सूची में है? |
| section `enterprise` | If you are starting a business | तुम्ही व्यवसाय सुरू करत असाल तर | यदि आप व्यवसाय शुरू कर रहे हैं |
| Q `venture_type` | Is this your first business? | हा तुमचा पहिला व्यवसाय आहे का? | क्या यह आपका पहला व्यवसाय है? |
| &nbsp;&nbsp;opt `GREENFIELD` | Yes, my first | होय, हा माझा पहिला | हां, यह मेरा पहला है |
| &nbsp;&nbsp;opt `EXISTING` | No, I already run one | नाही, मी आधीच एक चालवतो | नहीं, मैं पहले से एक चला रहा हूं |
| Q `loan_amount` | How much do you need to borrow, in rupees? | तुम्हाला किती कर्ज हवे आहे, रुपयांमध्ये? | आपको कितना कर्ज़ चाहिए, रुपयों में? |
| section `declarations` | A few things to declare | काही गोष्टी जाहीर करायच्या आहेत | कुछ बातें घोषित करनी हैं |
| Q `paid_income_tax` | Did you pay income tax last year? | तुम्ही मागील वर्षी आयकर भरला होता का? | क्या आपने पिछले वर्ष आयकर भरा था? |
| Q `government_employee` | Are you, or were you, a government employee, other than Multi Tasking Staff, Class IV or Group D? | मल्टी टास्किंग स्टाफ, वर्ग चार किंवा गट ड वगळता, तुम्ही सरकारी कर्मचारी आहात किंवा होता का? | मल्टी टास्किंग स्टाफ, वर्ग चार या समूह घ को छोड़कर, क्या आप सरकारी कर्मचारी हैं या रह चुके हैं? |
| Q `constitutional_post` | Have you held a constitutional post, or been a minister, legislator, mayor or district panchayat chairperson? | तुम्ही घटनात्मक पद भूषवले आहे का, किंवा मंत्री, आमदार खासदार, महापौर अथवा जिल्हा पंचायत अध्यक्ष राहिला आहात का? | क्या आपने कोई संवैधानिक पद संभाला है, या मंत्री, विधायक सांसद, महापौर अथवा जिला पंचायत अध्यक्ष रहे हैं? |
| Q `registered_professional` | Are you a practising doctor, engineer, lawyer, chartered accountant or architect registered with a professional body? | तुम्ही व्यावसायिक संस्थेकडे नोंदणीकृत आणि प्रत्यक्ष व्यवसाय करणारे डॉक्टर, अभियंता, वकील, सनदी लेखापाल किंवा वास्तुविशारद आहात का? | क्या आप किसी व्यावसायिक संस्था में पंजीकृत और प्रैक्टिस करने वाले डॉक्टर, इंजीनियर, वकील, चार्टर्ड अकाउंटेंट या वास्तुकार हैं? |
| Q `institutional_landholder` | Is the land held by an institution rather than by a person? | जमीन एखाद्या व्यक्तीच्या नावे नसून संस्थेच्या नावे आहे का? | क्या ज़मीन किसी व्यक्ति के बजाय किसी संस्था के नाम है? |
| Q `monthly_pension` | Pension from service other than Multi Tasking Staff, Class IV or Group D: how much do you receive each month, in rupees? | मल्टी टास्किंग स्टाफ, वर्ग चार किंवा गट ड वगळता इतर सेवेतून मिळणारे निवृत्तिवेतन: तुम्हाला दरमहा किती मिळते, रुपयांमध्ये? | मल्टी टास्किंग स्टाफ, वर्ग चार या समूह घ को छोड़कर अन्य सेवा से मिलने वाली पेंशन: आपको हर महीने कितनी मिलती है, रुपयों में? |
| section `study` | About your studies | तुमच्या शिक्षणाबद्दल | आपकी पढ़ाई के बारे में |
| Q `class_level` | Which class are you in at school? Leave this blank if you have finished school. | तुम्ही शाळेत कोणत्या इयत्तेत आहात? शाळा पूर्ण झाली असल्यास हे रिकामे ठेवा. | आप स्कूल में किस कक्षा में हैं? यदि स्कूल पूरा हो चुका है तो इसे खाली छोड़ दें. |
| Q `school_recognised` | Are you a regular, full time student at a government school, or a school recognised by the government or a Central or State Board? | तुम्ही सरकारी शाळेत, किंवा शासनमान्य अथवा केंद्रीय वा राज्य मंडळाची मान्यता असलेल्या शाळेत नियमित पूर्णवेळ विद्यार्थी आहात का? | क्या आप किसी सरकारी स्कूल में, या सरकार अथवा केंद्रीय या राज्य बोर्ड से मान्यता प्राप्त स्कूल में नियमित पूर्णकालिक विद्यार्थी हैं? |
| Q `admission_secured` | Have you secured admission to a full time course at a college or institution? | तुम्हाला महाविद्यालयात किंवा संस्थेत पूर्णवेळ अभ्यासक्रमासाठी प्रवेश मिळाला आहे का? | क्या आपको किसी कॉलेज या संस्थान में पूर्णकालिक पाठ्यक्रम में दाखिला मिल गया है? |
| Q `year_of_study` | Which year of that course are you in? | तुम्ही त्या अभ्यासक्रमाच्या कितव्या वर्षात आहात? | आप उस पाठ्यक्रम के कौन से वर्ष में हैं? |
| Q `other_central_prematric_scholarship` | Are you receiving another centrally funded pre-matric scholarship, other than the National Means-cum-Merit scholarship? | राष्ट्रीय आर्थिक दुर्बल घटक गुणवत्ता शिष्यवृत्ती वगळता, तुम्हाला केंद्र पुरस्कृत दुसरी मॅट्रिकपूर्व शिष्यवृत्ती मिळते का? | राष्ट्रीय आय-सह-योग्यता छात्रवृत्ति को छोड़कर, क्या आपको केंद्र द्वारा वित्तपोषित कोई अन्य मैट्रिक-पूर्व छात्रवृत्ति मिल रही है? |
| section `documents` | Which of these do you have with you? | यांपैकी कोणती कागदपत्रे तुमच्याकडे आहेत? | इनमें से कौन से दस्तावेज़ आपके पास हैं? |
| Q `documents_held` | Tick every document you can produce. | तुम्ही दाखवू शकाल अशा प्रत्येक कागदपत्रावर खूण करा. | आप जो भी दस्तावेज़ दिखा सकते हैं, उन सब पर निशान लगाएं. |

## Not covered here

**Scheme rules themselves are never translated.** Every quoted clause stays in the
language the government published it in, because a translated legal clause is no
longer the clause. The surrounding sentence is translated; the quote is not.

## Highest priority: the possessive frame around the death certificate

This is the single most-shown sentence in the product, and it is the one a widow reads
first. It was wrong in English too until 2026-08-26 (it said "Bring your death
certificate", as if the certificate were hers), and fixing the label has left a
grammar question in both Indian languages that a native speaker has to settle.

The frame supplies the possessive and the slot now supplies a genitive noun phrase:

| | frame | renders as |
|---|---|---|
| mr | `तुमचा {document} आणा` | तुमचा पतीचा मृत्यू दाखला आणा |
| hi | `अपना {document} लाइए` | अपना पति का मृत्यु प्रमाणपत्र लाइए |

Both read as though the determiner should be oblique — `तुमच्या पतीचा` and `अपने पति
का`. If that is right, the fix is NOT to edit the label: it is to give this document its
own sentence key, because changing `तुमचा` to `तुमच्या` in the shared frame would break
every other document, which are all direct-case ("तुमचा आधार आणा" is correct).

Please answer just this: is the rendered sentence acceptable as it stands, or does it
need its own frame?


## Added 2026-08-30: the disclaimer

- [x] Reviewed

`web/src/strings.js`, key `disclaimer`, in all three languages. Drafted, not reviewed.

This one is different from everything above it. It is not a label a citizen can shrug
off if it reads oddly; it is the sentence that says Haqdaar does not speak for the
government. It sits at the foot of every screen, under a masthead carrying the
national colours and a chakra. If the Marathi or Hindi wording is weak, the English
promise is the only one that actually got made.

| | |
|---|---|
| **en** | Haqdaar is not an official Government of India service, and is not affiliated with any ministry or department. It reads published scheme rules and shows what they say; only the department concerned can approve an application. |
| **mr** | हक्कदार ही भारत सरकारची अधिकृत सेवा नाही, आणि कोणत्याही मंत्रालयाशी किंवा विभागाशी संलग्न नाही. ती प्रकाशित योजनांचे नियम वाचते आणि ते काय सांगतात ते दाखवते; अर्ज मंजूर करण्याचा अधिकार फक्त संबंधित विभागाला आहे. |
| **hi** | हक़दार भारत सरकार की आधिकारिक सेवा नहीं है, और किसी भी मंत्रालय या विभाग से संबद्ध नहीं है। यह प्रकाशित योजना नियमों को पढ़ता है और वे क्या कहते हैं यह दिखाता है; आवेदन स्वीकृत करने का अधिकार केवल संबंधित विभाग को है। |

Three things to check, in order of how much they cost if wrong:

1. **"not affiliated" must stay absolute.** Marathi `संलग्न नाही` and Hindi `संबद्ध नहीं`
   should read as a flat denial of any connection, not as "not directly involved".
2. **The second clause must not promise approval.** `अर्ज मंजूर करण्याचा अधिकार फक्त
   संबंधित विभागाला आहे` has to keep the sense that approval belongs to the
   department ALONE. It is the same promise the verdict cards make, and softening it
   here contradicts them.
3. **Check the app name in each script.** `हक्कदार` in Marathi and `हक़दार` in Hindi,
   matching `appName`. The nukta on क़ is easy to lose in a copy-paste.

Note this section is prose, not a template: there are no `{slot}` values and no
numbers, so the build audit cannot catch a bad translation here. Only a reader can.


## Added 2026-08-30: the front door and the demo profile labels

- [x] Reviewed

`web/src/strings.js`, keys `verticals` and `who`, in Marathi and Hindi. Drafted, not
reviewed.

These were English constants inside `App.jsx` until now, so on a Marathi or Hindi page
the three front-door buttons and every demo profile label rendered in English. That is
the FIRST thing on the screen after the heading, which makes it the worst possible
place for it. Reported from use, not caught by a test.

`verticals` — the three doors. Each has a `door` (the button), an `eg` (the examples
under it) and a `group` (the heading over the results):

| | door | eg |
|---|---|---|
| **mr** entrepreneur | व्यवसाय सुरू करणे किंवा चालवणे | कर्ज, भांडवल, स्वतःच्या कामासाठी अनुदान |
| **mr** welfare | उत्पन्न, निवृत्तिवेतन आणि कौटुंबिक आधार | वैधव्य, वृद्धापकाळ, शेती, आरोग्य विमा |
| **mr** student | शिक्षणाचा खर्च भागवणे | शाळा व महाविद्यालयीन शिष्यवृत्ती |
| **hi** entrepreneur | व्यवसाय शुरू करना या चलाना | ऋण, पूंजी, अपने काम के लिए सब्सिडी |
| **hi** welfare | आय, पेंशन और पारिवारिक सहायता | वैधव्य, वृद्धावस्था, खेती, स्वास्थ्य कवर |
| **hi** student | शिक्षा का खर्च उठाना | स्कूल और कॉलेज छात्रवृत्ति |

What to check:

1. **`door` is what she picks herself from, before she has told us anything.** It has
   to describe a SITUATION she recognises, not a scheme category. "Income, pension and
   family support" works because a widow reads it and thinks yes, that is me.
2. **`eg` must not read as a promise.** These are examples of what the door covers,
   not a list of what she will get.
3. **Caste wording in `who`.** `अनुसूचित जाती` / `अनुसूचित जाति` is the formal term and
   is what the corpus uses. It should not be softened or swapped for a colloquialism.
4. **Sunita's label keeps ASCII digits** (`60`), matching how numbers reach the screen
   everywhere else in the UI. Do not convert to Devanagari numerals here.

Like the disclaimer section above, this is prose with no slots and no template audit
behind it. Nothing will go red if it is wrong.
