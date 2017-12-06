import json, io
import random
import datetime

def condition_sentence(pronoun, conds):
    if len(conds) > 1:
        return pronoun + " is experiencing " + ", ".join(conds[:-1]).lower() + " and " + conds[-1].lower() + ".\n"
    elif len(conds) == 1:
        return pronoun + " is experiencing " + conds[0].lower() + ".\n"
    return ''

def prescription_sentence(pronoun, pres):
    if len(pres) > 1:
        return pronoun + " currently takes " + ", ".join(pres[:-1]).lower() + " and " + pres[-1].lower() + ".\n"
    elif len(pres) == 1:
        return pronoun + " is prescribed " + pres[0].lower() + ".\n"
    return ''

def fill_note(name, age, sex, pronoun, weight, doctor, conds, pres, diagnosis):
    filler_sentences = [
        'Capoten caused a cough. ',
        pronoun + ' works in computer software. ',
        pronoun + ' does not smoke. ',
        pronoun + ' drinks wine and Martinis "probably more than I need to." ',
        pronoun + ' smokes between one and two packs of cigarettes a day. ',
        pronoun + ' reports ' + pronoun + ' is overall doing well. ',
        'Return to clinic in 6 months. ', 
        pronoun + ' will let us know if back pain gets any worse. ',
        'Check lipids and ALT today. ',
        'No cough. ',
        'No abdominal pain or change in bowel habits. ',
        'Also check CBC, calcium, sed rate and PSA. ',
        'Regular rate and rhythm without murmur. ',
        'Sulfa caused a rash. ',
        'No abdominal pain or change in bowel habits. ',
        'Possible recurrence of pilonidal cyst. ',
        'Last July ' + pronoun + ' presented with more pain in this area. ',
        pronoun + ' did have some more knee pain for a few weeks, but this has resolved. ',
        pronoun + ' is having more trouble with his sinuses. ',
        'Over the past couple weeks ' + pronoun + ' has had significant congestion and thick discharge. ',
        'No fevers or headaches but does have diffuse upper right-sided teeth pain. ',
        pronoun + ' denies any chest pains, palpitations, PND, orthopnea, edema or syncope. ',
        'No edema. ',
        'Return to clinic in six months. ',
        'No lymphadenopathy. ',
        'Clear lungs. ',
        'Strength, sensation and DTRs intact. ',
        'Again, recommended diet and exercise changes. ',
        'No palpitations, PND, orthopnea or edema. ',
        'Midepigastric pain. More likely GI in origin. ',
        'Probable peripheral vascular disease. ',
        'Looks well. ',
        'Tobacco abuse. ' + pronoun + ' was again told that ' + pronoun + ' needs to quit and encouraged to use the patches. ',
        'Straight leg raise negative. ',
        'No drug use. ',
        'Slept poorly. ',
        pronoun + ' appeared very alert and cooperative. ',
        pronoun + ' is very frustrated with trying to diet because ' + pronoun + ' always feels hungry. ',
        pronoun + ' reports mild burning with urination. ',
        'Increase fluid intake, avoid alcoholic beverages. ',
        pronoun + ' feels swelling in feet has improved but still has to elevate legs frequently. ',
        pronoun + ' appears energetic and in no distress. ',
        pronoun + ' has tried cough medicine with no relief. ',
        pronoun + ' will continue to use Tylenol for pain relief. ',
        pronoun + ' was informed that ' + pronoun + 'may continue to experience pain after the rash resolves. ',
        pronoun + ' should return to clinic if pain becomes more severe. ',
        'Recent onset of cough and SOB. ',
        'Educated patient on inhaler usage. ',
        'Advised patient to quit smoking. ',
        'Follow up in clinic tomorrow. ',
        'If symptoms are worse, call the on-call physician or go to the ER. ',
        pronoun + ' first noticed that ' + pronoun + ' felt tired when working long hours to get a job done at work. ',
        pronoun + ' describes fatige as "feeling limp". ',
        pronoun + ' has no alopecia or skin changes. ',
        pronoun + ' has had no fever, chills or night sweats. ',
        pronoun + ' does not feel depressed mood, sadness, or anhedonia. ',
        'Recent onset of fatigue with no obvious inciting event. ',
        'Hypothyroidism is possible. ',
        'Continue with current treatment plan. ',
        
    ]
    intro = name + ' is a ' + age + '-year-old ' + sex + '. ' + pronoun + ' weighs ' + weight + ' lbs.\n'
    has = condition_sentence(pronoun, conds)
    takes = prescription_sentence(pronoun, pres)
    bp = "Blood pressure " + str(random.randint(70,150)) + "/" + str(random.randint(40,100)) + ", pulse " + str(random.randint(40,200)) + ".\n"
    end = "\nSeen by " + doctor

    sentences = [has, takes, bp]
    sentences.extend(random.sample(filler_sentences, random.randint(1,8)))
    if len(diagnosis):
        sentences.append(diagnosis)
    note = intro + ''.join(random.sample(sentences, len(sentences))) + end
    return note

def get_age(bd):
    today = datetime.date.today()
    return today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day))


random.seed(666)
conditions = ['shortness of breath', 'chest pain', 'syncope', 'asthma', 'pneumonia', 'leg pain', 'infection', 'pelvic pain', 'dizziness', 'seizures', 'alcoholism', 'arthritis', "Allergy","Alzheimer's", "Dementia","Anemia","Anxiety Disorder","Arthritis","Asthma","Hypertension","Breast Health and Disease","Bursitis", "Tendonitis","Cholesterol","Cold", "Flu","Depression","Diabetes","Digestive Disorder","Fatigue and Low Energy","Foot Problems","Grief and Loss","Headache","Hearing Loss","Kidney Disease","Lung Disease","Memory Loss","Menopause","Osteoporosis","Pain, Back","Generalized Pain","Hand Pain","Hip Pain","Knee Pain","Neck Pain","Parkinson's Disease","Pregnancy","Prostate Disease","Sleep Disorder","Stress","Stroke","Thyroid Disorder","Urine and Bladder Problems"]
prescriptions = ['amoxicillin', 'fluoxetine', 'sulfa', 'acetaminophen', 'ibuprofen', 'naproxen sodium', 'ondansetron', 'metformin', 'atorvastatin', 'lisinopril', 'gabapentin', 'prednisone', 'levothyroxine', 'hydrocodone']
rd1 = ['PPES', 'Purple People Eater Syndrome']
rd2 = ['Pumpkinitis', 'PKS']
prob = [True, False, False, False] # simulate 1/4 of patients with rd
symptoms = ['purple tongue', 'singing']
doctors = ['Victor Frankenstein, MD', 'Jane Casper, MD', 'Frank Dracula, MD', "Jackie O'Lantern, MD", 'Edgar Allen Poe, MD']
patient_csv = 'patient.csv'
patients = []
with open(patient_csv, 'r') as f:
    text = f.read().split('\n')
    for line in text:
        p = line.split('|')
        if len(p) > 1:
            patients.append({
                'id': p[0],
                'name': p[1],
                'date_of_birth': datetime.datetime.strptime(p[2], "%m-%d-%y"),
                'sex': p[6]
            })

notes = []
for patient in patients:
    age = get_age(patient['date_of_birth'])
    pronoun = 'He' if patient['sex'] == 'M' else 'She'
    weight = random.randint(100, 300)
    doctor = random.choice(doctors)
    num_notes = random.randint(1,250)
    diagnosis = ''
    conds = []
    pres = []

    if random.choice(prob):
        ppes = random.randint(0,1)
        if ppes:
            conds.extend(symptoms)
            not_diag = random.randint(0,3)
            if not not_diag:
                diagnosis = 'Patient diagnosed with ' + random.choice(rd1) + '.\n'
                pres.append('candy corn')
            print("B")
        else:
            conds.append(random.choice(symptoms))
            not_diag = random.randint(0,3)
            if not not_diag:
                diagnosis = 'Patient diagnosed with ' + random.choice(rd2) + '.\n'
                pres.append('candy corn')
            print("A")
    else:
        print("N")

    for n in range(0,num_notes):
        conds.extend(random.sample(conditions, random.randint(0,5)))
        pres.extend(random.sample(prescriptions, random.randint(0,3)))
        note = fill_note(patient['name'], str(age), patient['sex'], pronoun, str(weight), doctor, conds, pres, diagnosis)
        notes.append({'id': len(notes), 'patient': patient['id'], 'note': note})

print(len(notes))
with open('notes.json', 'a+') as f:
    f.write(json.dumps(notes))
