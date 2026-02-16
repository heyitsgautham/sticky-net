import json, os

folders = ['government_scam', 'delivery_scam', 'romance_scam', 'tech_support_scam']
base = os.path.join(os.path.dirname(__file__), 'scenarios')
total = 0
errs = []

for folder in folders:
    path = os.path.join(base, folder)
    files = sorted(f for f in os.listdir(path) if f.endswith('.json'))
    for fname in files:
        with open(os.path.join(path, fname)) as f:
            d = json.load(f)
        total += 1
        fake = d['fakeData']
        turns = d['turns']
        valid_keys = {'bankAccount', 'upiId', 'phoneNumber', 'phishingLink', 'emailAddress'}
        for k in fake:
            if k not in valid_keys:
                errs.append(fname + ': bad key ' + k)
        for k, v in fake.items():
            if not any(v in t['scammer_message'] for t in turns):
                errs.append(fname + ': ' + k + '=' + v + ' missing from messages')
        for t in turns:
            for ext in t['expected_extractions']:
                if ext not in fake:
                    errs.append(fname + ' t' + str(t['turn']) + ': ' + ext + ' not in fakeData')
                elif fake[ext] not in t['scammer_message']:
                    errs.append(fname + ' t' + str(t['turn']) + ': ' + ext + ' val missing')
        print('OK ' + fname + ': ' + str(len(turns)) + ' turns')

print('Total: ' + str(total))
print('Errors: ' + str(len(errs)))
for e in errs:
    print('  X ' + e)
if not errs:
    print('All passed')
