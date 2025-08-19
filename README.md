# SP Smart Vending Machine Project

## Overview

### For Customers
The **Smart Vending Machine** allows customers to purchase drinks either:
- Directly at the vending machine (powered by Raspberry Pi), or  
- Online via a dedicated mobile-friendly website.

The vending machine hardware also incorporates several advanced features (see **Hardware Features** below).

Through the Raspberry Pi, customers can:
1. Scroll through selection menu to select which drinks that they want 
2. Make payment via RFID or QR codes and receive drink


Through the website, customers can:
1. **Purchase drinks online** – Select items, make payment, and receive a unique **QR code**.
2. **Collect purchases** – Scan the QR code at the vending machine's Pi camera to dispense the drink.
3. **Play an interactive math game** – While waiting (e.g., in a queue), customers can play a fun quiz to earn small incentives. Upon successful completion, collection details are sent via email.





### For Staff (Maintenance & Management)
The staff dashboard is accessible only to **authorized personnel** via secure login.  
Once logged in, staff can:
- Add, edit, or remove drinks from the menu.
- Modify drink details such as **price**, **name**, and **stock level**.
- Add new staff accounts to the database to delegate maintenance duties.

[Project Demo – Staff Side](https://drive.google.com/file/d/1F3T52a-qFDyR8ml4HQwUIk_j81i8nhAm/view?usp=drive_link)



## Software Information

### Tech Stack
<!-- Add an image or diagram here -->
*(Tech stack diagram placeholder)*

### Main Purpose
The primary goal is to allow customers to purchase drinks via the website.  
**Workflow:**
1. Customer selects a drink and completes payment.
2. Website generates a **QR code** unique to the transaction.
3. Customer scans the QR code at the vending machine’s Pi camera.
4. The vending machine verifies the code and dispenses the drink.

[Project Demo – Main System](https://drive.google.com/file/d/1F3ghRg9FW2_wOZbbqDkroqWgERMRdN-q/view?usp=drive_link)



### Website Game
The website includes an **interactive math quiz** with the following rules:
- **Error detection system** – The game ends automatically if the player makes 3 incorrect answers.
- **Time limit** – Each quiz session lasts for a maximum of 2 minutes.
- **Reward system** – Upon successful completion, the player receives a small incentive, with collection details sent via email.

[YouTube Demo – Game](https://drive.google.com/file/d/1FSfaKCaYUKysUuDTu9PEJMXmDsHMvx0O/view?usp=drive_link)




## Hardware Features
*(Details to be added – e.g., cooling system, payment integration, internal condition sensors, etc.)*  
Please update this section with your hardware specifications.

Admin Mode:
1. Switch flipped from logic '0' to logic '1' to access Admin mode.
2. Admin will be prompted to key in passcode (actual passcode:1234)
>>condition 1 : When user fails to key in correct passcode, user will be prompted to key in passcode again
>>condition 2: When user keys in correct passcode, they will be able to access granted & servo motor open (stimulate vending machine door open)
                >> Admin can edit stock from herre
3. If there's a condition where user wants to retype passcode, they can press the '*' button to key in code again.

Remote Access: 
1. DHT11 sensor monitors temperature value in vending machine
2. If the temperature of the internals of the vending machines falls below predefined thresholds, (e.g., 2°C–8°C for cold drinks), email will be sent to technician to alert them.

Burglar detection:
1. IR sensor detects for tampering and unauthorized detection.
2. When the IR sensor detects something, Buzzer will ring for 10 seconds
3. camera will capture image of burglar and send it the telegram bot

Shaking of vending machine(security reasons):
1. When the Vending machine is being shaken vigorously, the buzzer will beep for 5 seconds,
2. camera will capture image of burglar and send it to telegram bot.

Math quiz game(fun factor):
1. After user has purchased a drink, vending machine will ask users if they would like to play a minigame to win a drink
if user selects yes:
    >>quiz starts:
       When user gets a question wrong: display "nice try!" message and go low power mode.
       When user gets all questions correct: Dispense a random drink.
if user selectes No:
    >> Machine goes to low power mode.

Payment method for physical payment:
1.User will be prompted if they would like to pay using QR code or via Card
    condition 1: When user selects QR code
        >> QR code will pop up and users will scan it to make payment
    condition 2: WHen user selects payment by card
        >> User will be requested to tap card on rfid reader
2.Payment succession(for card payment)
   When payment is successful: "Payment successful" message would be shown and drinks will dispense. 
   When payment unsuccesful: "Payment unsuccessful" will be shown and users will be prompted to tap card on rfid reader again.


Power Management(for energy efficiency, sustainability purposes)
High power mode conditions(when initial state in low power mode):
1.When a key is pressed
2.When Ultrasound sensor detects somebody
Low power mode condirions(when initial state in high power mode):
1. When keypad inactive for 3 mins
2. When Ultrasound detects no one for 3 mins
3. When power off option ('0') is selected in main menu
4. After one ordering cycle and user does not want to play math game.

## Running the Website

### Option 1 – Via Docker
To run the website on a Raspberry Pi using Docker:

```bash
docker run -p 5000:5000 chunhoesdocker/raspberrypi
```

### Option 2 – Via Kubernetes
Create a YAML file with the following content:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: sqlite-pv
spec:
  accessModes:
    - ReadWriteMany       # Allow multiple pods to read/write
  capacity:
    storage: 1Gi
  hostPath:               # Local storage (for testing on single-node cluster)
    path: /mnt/data/sqlite-db
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: sqlite-pvc
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 1Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ecommerce-website-deployment
  labels:
    app: ecommerce-website
spec:
  replicas: 5
  selector:
    matchLabels:
      app: ecommerce-website
  template:
    metadata:
      labels:
        app: ecommerce-website
    spec:
      containers:
        - name: ecommerce-website
          image: chunhoesdocker/ecommerce_website:latest
          imagePullPolicy: Always
          ports:
            - containerPort: 5000
          volumeMounts:
            - name: sqlite-storage
              mountPath: /instance  # DB will live here
      volumes:
        - name: sqlite-storage
          persistentVolumeClaim:
            claimName: sqlite-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: ecommerce-website-service
spec:
  selector:
    app: ecommerce-website
  ports:
    - protocol: TCP
      port: 5000
      targetPort: 5000
  type: LoadBalancer

```
Apply the configuration:

```bash
kubectl apply -f <your_yaml_file>.yml
```

## Contributions

#### Chun Ho
- xxx

### Dennis
- xxx

### Titus
- xxx

### Matin
- xxx
