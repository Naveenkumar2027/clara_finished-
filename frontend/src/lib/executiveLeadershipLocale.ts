import type { Language } from '../context/LanguageContext';
import kannadaLocale from '@college-locales/kn.json';
import { uiText } from '../localization/uiCopy';

export type ExecutiveLeadershipCopy = {
  label: string;
  name: string;
  title: string;
  bio: string;
};

type KannadaExecutiveRoleHolders = {
  principal: { name: string; title: string; profile: string };
  vice_principal: { name: string; title: string; profile: string };
};

const kannadaExecutives = kannadaLocale.role_holders as KannadaExecutiveRoleHolders;

/** Dr. Manjunath T N — multilingual UI copy aligned with kiosk language. */
export const PRINCIPAL_COPY: Record<Language, ExecutiveLeadershipCopy> = {
  English: {
    label: 'Executive Profile',
    name: 'Dr. Manjunath T N',
    title: 'Principal',
    bio: 'Dr. Manjunath T N, Principal of Sai Vidya Institute of Technology, is an experienced academic and administrator with strong contributions to engineering education, research promotion, and institutional development, focusing on quality teaching, discipline, and holistic student growth while leading key initiatives that strengthen the college’s academic standards and industry relevance.',
  },
  Kannada: {
    label: uiText('Kannada', 'cards.leadership_profile'),
    name: kannadaExecutives.principal.name,
    title: kannadaExecutives.principal.title,
    bio: kannadaExecutives.principal.profile,
  },
  Hindi: {
    label: 'प्रोफ़ाइल',
    name: 'डॉ. मंजुनाथ टी एन',
    title: 'प्राचार्य',
    bio: 'डॉ. मंजुनाथ टी एन साई विद्या इंस्टीट्यूट ऑफ टेक्नोलॉजी के प्राचार्य हैं। वे एक अनुभवी शैक्षणिक व प्रशासक हैं, जिन्होंने इंजीनियरिंग शिक्षा, अनुसंधान और संस्थागत विकास में महत्वपूर्ण योगदान दिया है। वे गुणवत्तापूर्ण शिक्षण, अनुशासन और समग्र छात्र विकास पर केंद्रित रहकर ऐसी पहलों का नेतृत्व करते हैं जो कॉलेज की शैक्षणिक मानकों और उद्योग-सापेक्षता को मजबूत करती हैं।',
  },
  Tamil: {
    label: 'தலைமை அறிமுகம்',
    name: 'டாக்டர் மஞ்சுநாத் டி என்',
    title: 'முதல்வர்',
    bio: 'டாக்டர் மஞ்சுநாத் டி என் அவர்கள் சாயி வித்யா இன்ஸ்ட்டிட்யூட் ஆப் டெக்னாலஜியின் முதல்வர். பொறியியல் கல்வி, ஆய்வு உறுதுணை மற்றும் நிறுவன முன்னேற்றத்தில் அனுபவம் வாய்த்த தலைமை அதிகாரி. சிறந்த கற்பித்தல், ஒழுக்கம் மற்றும் மாணவர் முழுமையான வளர்ச்சி ஆகியவற்றில் கவனத்துடன், கல்லூரியின் கல்வித்தரத்தையும் தொழில்துறை முக்கியத்தையும் வலுப்படுத்தும் முக்கிய முனைப்புகளுக்குத் தலைமை தாங்குகிறார்.',
  },
  Telugu: {
    label: 'నాయకత్వ ప్రొఫైల్',
    name: 'డాక్టర్ మంజునాథ్ టి ఎన్',
    title: 'ప్రిన్సిపాల్',
    bio: 'డాక్టర్ మంజునాథ్ టి ఎన్ సాయి విద్యా ఇన్‌స్టిట్యూట్ ఆఫ్ టెక్నాలజీ ప్రిన్సిపాల్ గా ఉన్నారు. ఇంజినీరింగ్ విద్యా, పరిశోధన ప్రోత్సాహం మరియు సంస్థాగత అభివృద్ధిలో గణనీయ అనుభవం కలిగిన విద్యావేత్త మరియు నిర్వాహకులు. నాణ్యమైన బోధనా, అనుశాసనం మరియు విద్యార్థుల సమగ్రాభివృద్ధిపై దృష్టిపెట్టి పరిశ్రమకు దగ్గరగా ఉండే శైక్షణిక ప్రమాణాలను బలోపేతం చేయడంలో ప్రధాన కార్యక్రమాలకు నాయకత్వం వహిస్తారు.',
  },
  Malayalam: {
    label: 'നേതൃ പ്രൊഫൈൽ',
    name: 'ഡോ. മഞ്ജുനാഥ് ടി എൻ',
    title: 'പ്രിൻസിപ്പൽ',
    bio: 'ഡോ. മഞ്ജുനാഥ് ടി എൻ സായി വിദ്യാ ഇൻസ്റ്റിറ്റ്യൂറ്റ് ഒഫ് ടെക്നോളജിയുടെ പ്രിൻസിപ്പലാണ്. എഞ്ചിനീയറിംഗ് വിദ്യാഭ്യാസം, ഗവേഷണ പ്രോത്സാഹനം, സ്ഥാപന വികസനം എന്നിവയിൽ വിശാലമായ അനുഭവമുള്ള അദ്ധ്യാപക-ഭരണ വിദഗ്ധൻ. ഗുണമേമ്പമുള്ള ബോധനം, അച്ചടക്ക്, വിദ്യാർഥികളുടെ സമഗ്രമായ വളർച്ച എന്നിവ ലക്ഷ്യമാക്കി അക്കാദമിക് മാനദണ്ഡങ്ങളെയും ഗവേഷണ-വ്യാവസായിക ബന്ധം ഉറപ്പാക്കുന്ന ശ്രദ്ധേയമായ പരിപാടികൾക്ക് നേതൃത്വം നൽകുന്നു.',
  },
};

/** Dr. Lakshminarayanachari K */
export const VICE_PRINCIPAL_COPY: Record<Language, ExecutiveLeadershipCopy> = {
  English: {
    label: 'Executive Profile',
    name: 'Dr. Lakshminarayanachari K',
    title: 'Vice Principal & Dean Academics',
    bio: 'Dr. Lakshminarayanachari K serves as Vice Principal and Dean Academics at SVIT, supporting academic planning, curriculum implementation, and teaching quality enhancement, while also contributing to research and publications; he plays a key role in coordinating faculty, improving learning outcomes, and aligning academic processes with institutional goals and regulatory requirements.',
  },
  Kannada: {
    label: uiText('Kannada', 'cards.leadership_profile'),
    name: kannadaExecutives.vice_principal.name,
    title: kannadaExecutives.vice_principal.title,
    bio: kannadaExecutives.vice_principal.profile,
  },
  Hindi: {
    label: 'प्रोफ़ाइल',
    name: 'डॉ. लक्ष्मीनारायणाचारी के',
    title: 'उप प्राचार्य और शैक्षणिक डीन',
    bio: 'डॉ. लक्ष्मीनारायणाचारी के एसवीआईटी में उप प्राचार्य और शैक्षणिक डीन हैं। वे शैक्षणिक योजना, पाठ्यक्रम कार्यान्वयन और शिक्षण की गुणवत्ता सुधार का समर्थन करते हैं, साथ ही शोध व प्रकाशन में भी भूमिका निभाते हैं। संकाय समन्वय, सीखने के परिणामों में सुधार और शैक्षणिक प्रक्रियाओं को संस्थागत उद्देश्यों और नियामक आवश्यकताओं के अनुरूप ढालने में उनकी महत्वपूर्ण भागीदारी है।',
  },
  Tamil: {
    label: 'தலைமை அறிமுகம்',
    name: 'டாக்டர் லக்ஷ்மிநாராயணச்சாரி கே',
    title: 'துணை முதல்வர் மற்றும் கல்வி டீன்',
    bio: 'டாக்டர் லக்ஷ்மிநாராயணச்சாரி கே SVIT இல் துணை முதல்வரும் கல்வி டீனுமாக செயல்படுகிறார்; கல்வித்திட்டம், பாடத்திட்டச் செயல்பாடுகளும் கற்பித்தல் தர மேம்பாடுகளுக்குத் தொடர் ஆதாரமாய் இருக்கிறார். ஆய்வு வெளியீடுகளிலும் அவர் பங்களிக்கிறார்; ஆசிரியர் ஒத்துழைப்பு, கற்றல் முடிவுகள் மேம்பாடு, கல்விசார் செயல்முறையை உள்ளக இலக்குகளுக்கும் ஒழுங்குமுறை தேவைகளுக்கும் இசைவாக்குவது ஆகியவற்றில் அவரது பணி முக்கியமானது.',
  },
  Telugu: {
    label: 'నాయకత్వ ప్రొఫైల్',
    name: 'డాక్టర్ లక్ష్మీనారాయణాచారి కె',
    title: 'ఉప ప్రిన్సిపాల్ మరియు డీన్ ఎకడెమిక్స్',
    bio: 'డాక్టర్ లక్ష్మీనారాయణాచారి కె SVIT లో ఉప ప్రిన్సిపాల్ మరియు డీన్ ఎకడెమిక్స్ గా ఉన్నారు. అకడెమిక్ ప్రణాళికలు, పాఠ్య ప్రణాళిక అమలు మరియు బోధనా నాణ్యత మెరుగుదలకు ఆధారంగా నిలుస్తారు; పరిశోధన మరియు ప్రచురణలలో కూడా కృషి చేస్తారు. ఫ్యాకల్టీ సమన్వయం, నేర్పు ఫలితాల మెరుగుదల మరియు విద్యా ప్రక్రియలను సంస్థ లక్ష్యాలు మరియు నియంత్రణ అవసరాలకు అనుగుణంగా సమకూర్చడంలో వారి పాత్ర కీలకం.',
  },
  Malayalam: {
    label: 'നേതൃ പ്രൊഫൈൽ',
    name: 'ഡോ. ലക്ഷ്മೀനാരായണാചാരി കെ',
    title: 'ഉപ പ്രിൻസിപ്പൽ, അക്കാദമിക് ഡീൻ',
    bio: 'ഡോ. ലക്ഷ്മീനാരായണാചാരി കെ SVIT ലെ ഉപ പ്രിൻസിപ്പലും അക്കാദമിക് ഡീനുമാണ്. വിദ്യാഭ്യാസ ആസൂത്രണം, പാഠ്യക്രമ നടപ്പാക്കൽ, അധ്യാപന ഗുണനിലവാര മെച്ചപ്പെടുത്തൽ എന്നിവയ്ക്ക് പിന്തുണ നൽകുകയും ഗവേഷണ-പ്രസിദ്ധീകരണങ്ങളിൽ സംഭാവന നൽകുകയും ചെയ്യുന്നു. അധ്യാപകരെ ഏകോപിപ്പിക്കുക, പഠന ഫലങ്ങൾ മെച്ചപ്പെടുത്തുക, വിദ്യാഭ്യാസ പ്രക്രിയകൾ സ്ഥാപന ലക്ഷ്യങ്ങളും നിയന്ത്രണ ആവശ്യങ്ങളുമായി പൊരുത്തപ്പെടുത്തുക എന്നിവയിൽ അദ്ദേഹത്തിന്റെ പങ്ക് നിർണായകമാണ്.',
  },
};
