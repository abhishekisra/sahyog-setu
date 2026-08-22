"""Deterministic, template-based FAQ for a scheme's detail view -- built
purely from fields the admin already entered (eligibility, required
documents, mode of application, age/income limits, gender/caste/marital/
religion restrictions, DBT, Central vs State). No AI/LLM call: nothing here
can invent a fact the admin didn't actually enter, which matters because
these answers state real eligibility/financial facts a citizen may act on.

Called from schemes/apis.py:scheme() on the ALREADY-SERIALIZED, already-
translated dict (so a FAQ built for ?lang=hi automatically quotes the
Hindi eligibility/documents/application text, not the English original).
A question is skipped entirely -- not shown with an empty/"N/A" answer --
whenever the underlying field is blank or is the "open to everyone"
default, so the FAQ only ever lists real restrictions.

The QUESTION text and the synthesized (non-copied) ANSWER sentences below
are professional English by default, and only switch language when the
page's own ?lang= actually does -- same fallback-to-English convention as
every other piece of UI text on this page, not a fixed, always-Hindi
string. Only 'en' and 'hi' are defined for now; any other lang falls back
to English, exactly like TranslatableMixin.field_for() does for content
with no translation yet.
"""

GENDER_LABELS = {
    'en': {'0': 'Male', '1': 'Female', '2': 'Transgender'},
    'hi': {'0': 'पुरुष', '1': 'महिला', '2': 'ट्रांसजेंडर'},
}
CASTE_LABELS = {
    'en': {
        '0': 'General', '1': 'OBC', '2': 'SC', '3': 'ST',
        '4': 'Particularly Vulnerable Tribal Group (PVTG)',
    },
    'hi': {
        '0': 'सामान्य', '1': 'अन्य पिछड़ा वर्ग (OBC)', '2': 'अनुसूचित जाति (SC)',
        '3': 'अनुसूचित जनजाति (ST)', '4': 'विशेष रूप से कमजोर जनजातीय समूह (PVTG)',
    },
}
MARITAL_LABELS = {
    'en': {
        '0': 'Married', '1': 'Unmarried', '2': 'Widowed / Widower',
        '3': 'Divorced', '4': 'Separated',
    },
    'hi': {
        '0': 'विवाहित', '1': 'अविवाहित', '2': 'विधवा / विधुर',
        '3': 'तलाकशुदा', '4': 'अलग रह रहे',
    },
}
RELIGION_LABELS = {
    'en': {
        '0': 'Hindu', '1': 'Muslim', '2': 'Christian', '3': 'Sikh',
        '4': 'Parsi', '5': 'Buddhist', '6': 'Jain', '7': 'No Religion',
    },
    'hi': {
        '0': 'हिन्दू', '1': 'मुस्लिम', '2': 'ईसाई', '3': 'सिख',
        '4': 'पारसी', '5': 'बौद्ध', '6': 'जैन', '7': 'कोई धर्म नहीं',
    },
}

GENDER_ALL = {'0', '1', '2'}
CASTE_ALL = {'0', '1', '2', '3', '4'}
MARITAL_ALL = {'0', '1', '2', '3', '4'}
RELIGION_ALL = {'0', '1', '2', '3', '4', '5', '6', '7'}

TEXT = {
    'en': {
        'eligibility_q': 'Who is eligible for this scheme?',
        'documents_q': 'What documents are required for this scheme?',
        'apply_q': 'How can I apply for this scheme?',
        'age_q': 'What is the age limit for this scheme?',
        'age_a': 'Applicants must be between {0} and {1} years of age.',
        'income_q': 'Is there an income limit for this scheme?',
        'income_a': 'Yes, the annual family income must not exceed Rs. {0:,}.',
        'gender_q': 'Who can apply for this scheme based on gender?',
        'gender_a': 'This scheme is available only for: {0}.',
        'caste_q': 'Is there a category restriction for this scheme?',
        'caste_a': 'This scheme is restricted to the following categories: {0}.',
        'marital_q': 'Is there a marital status requirement for this scheme?',
        'marital_a': 'This scheme is available only for: {0}.',
        'religion_q': 'Is there a religion-based restriction for this scheme?',
        'religion_a': 'This scheme is restricted to individuals of the following religions: {0}.',
        'dbt_q': 'Does this scheme offer Direct Benefit Transfer (DBT)?',
        'dbt_a': "Yes, the benefit of this scheme is transferred directly to the applicant's bank account via Direct Benefit Transfer (DBT).",
        'state_q': 'Which state is this scheme applicable to?',
        'state_a': 'This is a State Government scheme, applicable to residents of {0}.',
        'central_q': 'Is this scheme applicable across India?',
        'central_a': 'Yes, this is a Central Government scheme applicable across India.',
    },
    'hi': {
        'eligibility_q': 'इस योजना के लिए कौन पात्र है?',
        'documents_q': 'इस योजना के लिए कौन से दस्तावेज़ चाहिए?',
        'apply_q': 'इस योजना के लिए आवेदन कैसे करें?',
        'age_q': 'इस योजना के लिए आयु सीमा क्या है?',
        'age_a': 'आवेदक की आयु {0} से {1} वर्ष के बीच होनी चाहिए।',
        'income_q': 'क्या इस योजना के लिए आय की कोई सीमा है?',
        'income_a': 'हाँ, परिवार की वार्षिक आय ₹{0:,} से अधिक नहीं होनी चाहिए।',
        'gender_q': 'यह योजना किस लिंग के लिए है?',
        'gender_a': 'यह योजना केवल {0} के लिए उपलब्ध है।',
        'caste_q': 'क्या इस योजना में श्रेणी (जाति) संबंधी कोई शर्त है?',
        'caste_a': 'यह योजना केवल इन श्रेणियों के लिए है: {0}।',
        'marital_q': 'क्या वैवाहिक स्थिति की कोई शर्त है?',
        'marital_a': 'यह योजना केवल इनके लिए है: {0}।',
        'religion_q': 'क्या इस योजना में धर्म संबंधी कोई शर्त है?',
        'religion_a': 'यह योजना केवल इन धर्मों के लोगों के लिए है: {0}।',
        'dbt_q': 'क्या इस योजना का लाभ DBT (Direct Benefit Transfer) से मिलता है?',
        'dbt_a': 'हाँ, इस योजना का लाभ Direct Benefit Transfer (DBT) के माध्यम से सीधे आवेदक के बैंक खाते में भेजा जाता है।',
        'state_q': 'यह योजना किस राज्य के लिए है?',
        'state_a': 'यह एक राज्य सरकार की योजना है, जो {0} राज्य के निवासियों के लिए है।',
        'central_q': 'क्या यह योजना पूरे भारत में लागू है?',
        'central_a': 'हाँ, यह एक केंद्र सरकार की योजना है जो पूरे भारत में लागू है।',
    },
}


def _csv_codes(raw):
    return {c.strip() for c in (raw or '').split(',') if c.strip()}


def _restriction_labels(raw, label_map, all_set):
    """None when every code in all_set is present (open to everyone -- the
    common case, myscheme.gov.in imports and most manual entries both use
    this convention) or when the field is blank -- either way there's no
    real restriction worth asking a question about."""
    codes = _csv_codes(raw)
    if not codes or codes >= all_set:
        return None
    return [label_map[c] for c in sorted(codes) if c in label_map]


def build_scheme_faq(data, lang='en'):
    t = TEXT.get(lang, TEXT['en'])
    gender_labels_map = GENDER_LABELS.get(lang, GENDER_LABELS['en'])
    caste_labels_map = CASTE_LABELS.get(lang, CASTE_LABELS['en'])
    marital_labels_map = MARITAL_LABELS.get(lang, MARITAL_LABELS['en'])
    religion_labels_map = RELIGION_LABELS.get(lang, RELIGION_LABELS['en'])

    faq = []

    if data.get('eligibility'):
        faq.append({'q': t['eligibility_q'], 'a': data['eligibility']})

    if data.get('required_documents'):
        faq.append({'q': t['documents_q'], 'a': data['required_documents']})

    if data.get('mode_of_application'):
        faq.append({'q': t['apply_q'], 'a': data['mode_of_application']})

    age_min, age_max = data.get('age_min'), data.get('age_max')
    if age_min not in (None, '') and age_max not in (None, '') and not (int(age_min) <= 0 and int(age_max) >= 100):
        faq.append({'q': t['age_q'], 'a': t['age_a'].format(age_min, age_max)})

    income_max = data.get('income_max')
    if income_max not in (None, '', 0):
        faq.append({'q': t['income_q'], 'a': t['income_a'].format(int(income_max))})

    gender_labels = _restriction_labels(data.get('scheme_for'), gender_labels_map, GENDER_ALL)
    if gender_labels:
        faq.append({'q': t['gender_q'], 'a': t['gender_a'].format(', '.join(gender_labels))})

    caste_labels = _restriction_labels(data.get('castes'), caste_labels_map, CASTE_ALL)
    if caste_labels:
        faq.append({'q': t['caste_q'], 'a': t['caste_a'].format(', '.join(caste_labels))})

    marital_labels = _restriction_labels(data.get('marital_status'), marital_labels_map, MARITAL_ALL)
    if marital_labels:
        faq.append({'q': t['marital_q'], 'a': t['marital_a'].format(', '.join(marital_labels))})

    religion_labels = _restriction_labels(data.get('religions'), religion_labels_map, RELIGION_ALL)
    if religion_labels:
        faq.append({'q': t['religion_q'], 'a': t['religion_a'].format(', '.join(religion_labels))})

    if data.get('dbt'):
        faq.append({'q': t['dbt_q'], 'a': t['dbt_a']})

    if data.get('scheme_type') == 1 and data.get('state'):
        faq.append({'q': t['state_q'], 'a': t['state_a'].format(data['state'])})
    elif data.get('scheme_type') == 0:
        faq.append({'q': t['central_q'], 'a': t['central_a']})

    return faq
