import csv

with open("metadata_train.csv", "r", encoding="utf-8") as f_in, \
     open("output2.csv", "w", encoding="utf-8-sig", newline="") as f_out:

    reader = csv.reader(f_in, delimiter="|")
    writer = csv.writer(f_out)

    for row in reader:
        writer.writerow(row)