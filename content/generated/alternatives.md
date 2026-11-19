# Alternativne replike roditelja po nivou ljutnje

Generisano komandom `python -m src.alternatives` (pravila, bez jezičkog modela). Isti potez i isti sadržaj, različit nivo ljutnje; u zagradi je izmereni nivo.

## bad_grade

### OPEN_COMPLAINT (opening)

*Smernica:* Say who you are and why you are calling. State the main complaint. Do not ask questions yet.

*Vanila rečenica:* Hello, this is Mr. Markovic, Luka's father. I am calling about the grade Luka got on the math test last Thursday. I think the grade is not fair.

- **1 – calm** (1): Hello, this is Mr. Markovic, Luka's father. I am calling about the grade Luka got on the math test last Thursday. I think the grade is not fair.
- **2 – dissatisfied** (2): Hello, this is Mr. Markovic, Luka's father. I am calling about the grade Luka got on the math test last Thursday. The grade is not fair. I expected a call from the school first.
- **3 – angry** (3): Hello, this is Mr. Markovic, Luka's father. I am calling about the grade Luka got on the math test last Thursday. The grade is completely unfair. This makes no sense!
- **4 – very angry** (4): Hello, this is Mr. Markovic, Luka's father. I am calling about the grade Luka got on the math test last Thursday. The grade is absolutely unfair! This is ridiculous!
- **5 – about to hang up** (5): Hello, this is Mr. Markovic, Luka's father. I am calling about the grade Luka got on the math test last Thursday. The grade is absolutely unfair! I am sick and tired of this! I want answers right NOW!

### ELABORATE_COMPLAINT (complaint)

*Smernica:* Answer what the teacher asked. Add exactly one new fact: Luka studied for this test for three days. Keep the main complaint.

*Vanila rečenica:* Luka studied for this test for three days. So I would like to understand how this happened.

- **1 – calm** (1): Luka studied for this test for three days. So I would like to understand how this happened.
- **2 – dissatisfied** (2): Luka studied for this test for three days. So I want to understand how this happened. Frankly, this is disappointing.
- **3 – angry** (2): Luka studied for this test for three days. So I want to understand how this happened. This is unacceptable!
- **4 – very angry** (4): Look, Luka studied for this test for three days. So I want to understand how this happened! Do you even check these things properly?
- **5 – about to hang up** (5): Luka studied for this test for three days. So I want to understand how this happened! This is a disgrace! Explain it to me, right NOW!

### RAISE_COMPLAINT (complaint)

*Smernica:* Bring up the next problem in one or two sentences: Nobody told me that Luka was struggling in math. I had to find out from a failing grade.

*Vanila rečenica:* And there is something else. Nobody told me that Luka was struggling in math. I had to find out from a failing grade.

- **1 – calm** (1): And there is something else. Nobody told me that Luka was struggling in math. I had to find out from a failing grade.
- **2 – dissatisfied** (2): And there is something else. Nobody told me that Luka was struggling in math. I had to find out from a failing grade. That is not how it should work.
- **3 – angry** (3): And there is something else. Nobody told me that Luka was struggling in math. I had to find out from a failing grade. I am really angry about this!
- **4 – very angry** (4): And there is something else. NOBODY told me that Luka was struggling in math. I had to find out from a failing grade! Do you even care about your students?
- **5 – about to hang up** (4): Enough. And there is something else. NOBODY told me that Luka was struggling in math. I had to find out from a failing grade! Unbelievable!

### REVEAL_HIDDEN_NEED (discussion)

*Smernica:* Say what really worries you: If this goes on, Luka could fail math this year, and it feels like nobody at school cares. One or two sentences. This is a softer moment.

*Vanila rečenica:* Honestly, I am worried. If this goes on, Luka could fail math this year, and it feels like nobody at school cares.

- **1 – calm** (1): Honestly, I am worried. If this goes on, Luka could fail math this year, and it feels like nobody at school cares.
- **2 – dissatisfied** (2): Honestly, I am worried. If this goes on, Luka could fail math this year, and it feels like nobody at school cares. I expected better.
- **3 – angry** (3): Honestly, I am really worried. If this goes on, Luka could fail math this year, and it feels like nobody at school cares. This makes no sense!

### ACKNOWLEDGE_PARTIALLY (discussion)

*Smernica:* Accept that the teacher understood you, but say that the problem is still there.

*Vanila rečenica:* Well, at least you see my point. But the grade is still a problem.

- **1 – calm** (2): Well, at least you see my point. But the grade is still a problem.
- **2 – dissatisfied** (3): Well, at least you see my point. But the grade is still a problem. Frankly, this is disappointing.
- **3 – angry** (3): Well, at least you see my point. But the grade is still a huge problem. This makes no sense!
- **4 – very angry** (4): Well, at least you see my point. But the grade is still a huge problem! Don't think nice words will fix this!

### REPEAT_COMPLAINT (discussion)

*Smernica:* Say that the teacher did not answer you and repeat the main complaint.

*Vanila rečenica:* You are not answering me. I said that the grade is not fair.

- **2 – dissatisfied** (2): You are not answering me. I said that the grade is not fair. I will say it again.
- **3 – angry** (3): You are not answering me. I said that the grade is completely unfair. I am really angry about this!
- **4 – very angry** (4): You are not answering me. I said that the grade is absolutely unfair! This is ridiculous! I have said it three times already!
- **5 – about to hang up** (5): No. Listen to me. You are not answering me. I said that the grade is absolutely UNFAIR! I am done repeating myself!

### DEMAND_ACTION (discussion)

*Smernica:* Demand a concrete action: change the grade or let Luka take the test again.

*Vanila rečenica:* I would like you to change the grade or let Luka take the test again.

- **3 – angry** (3): I demand that you change the grade or let Luka take the test again. And I want it this week!
- **4 – very angry** (4): I demand that you change the grade or let Luka take the test again! Do you even care about your students?
- **5 – about to hang up** (5): I demand that you change the grade or let Luka take the test AGAIN! This is a disgrace! Or the principal will hear about this!

### REJECT_RULES (discussion)

*Smernica:* The teacher hides behind the rules. Say that the rules do not solve your problem.

*Vanila rečenica:* I understand that there are rules, but the rules do not help Luka.

- **3 – angry** (2): I understand that there are rules, but the rules don't help Luka. This is unacceptable!
- **4 – very angry** (4): I understand that there are rules, but the rules don't help Luka! This is outrageous! Stop hiding behind the rules!
- **5 – about to hang up** (5): I understand that there are rules, but the rules don't help Luka! I have had ENOUGH! I don't want excuses, I want a solution!

### REJECT_EXPLANATION (discussion)

*Smernica:* The teacher gives facts while you are still angry. Say that the facts do not answer your complaint.

*Vanila rečenica:* That explanation does not help Luka at all.

- **3 – angry** (3): That explanation does nothing to help Luka at all. I am really angry about this!
- **4 – very angry** (4): That explanation does nothing to help Luka at all! Do you even care about your students? Don't lecture me!
- **5 – about to hang up** (5): That explanation does nothing to help Luka at all! I have had ENOUGH! I don't want excuses, I want a solution!

### ACCUSE (discussion)

*Smernica:* Blame the teacher for the problem and for the lack of communication. No new facts.

*Vanila rečenica:* I think the school did not do its job here. Nobody told me that Luka was struggling.

- **3 – angry** (3): The school did not do its job here. Nobody told me that Luka was struggling. This is unacceptable!
- **4 – very angry** (4): The school completely failed here. NOBODY told me that Luka was struggling! Do you even care about your students?
- **5 – about to hang up** (5): The school completely failed here. NOBODY told me that Luka was struggling! I am sick and tired of this! What kind of teacher does that?

### REJECT_PROPOSAL (discussion)

*Smernica:* Reject the teacher's proposal. Say that first you want an answer about the main complaint.

*Vanila rečenica:* That does not solve the problem for me yet. First I want an answer about the grade.

- **3 – angry** (3): That doesn't solve the problem for me yet. First I want an answer about the grade. This makes no sense!
- **4 – very angry** (4): That doesn't solve the problem for me yet. First I want an answer about the grade! This is ridiculous! You think that fixes everything?
- **5 – about to hang up** (5): That doesn't solve the problem for me yet. First I want an answer about the grade! I have had ENOUGH! Don't insult me with that!

### ASK_FOR_PLAN (resolution)

*Smernica:* Ask what exactly the teacher is going to do about the problem.

*Vanila rečenica:* So what exactly are you going to do about the grade?

- **1 – calm** (1): So what exactly are you going to do about the grade?
- **2 – dissatisfied** (2): So what exactly are you going to do about the grade? Frankly, this is disappointing.
- **3 – angry** (2): So what exactly are you going to do about the grade? This is unacceptable!
- **4 – very angry** (4): So what exactly are you going to do about the grade? This is outrageous! Well? I am waiting!

### CONDITIONAL_ACCEPT (resolution)

*Smernica:* Accept the teacher's proposal, but add one condition: you to tell me much earlier next time if Luka is struggling.

*Vanila rečenica:* That could work. But I also want you to tell me much earlier next time if Luka is struggling.

- **1 – calm** (1): That could work. But I also want you to tell me much earlier next time if Luka is struggling.
- **2 – dissatisfied** (2): That could work. But I also want you to tell me much earlier next time if Luka is struggling. And I will hold you to that.
- **3 – angry** (2): That could work. But I also want you to tell me much earlier next time if Luka is struggling. This makes no sense!

### ACCEPT_PROPOSAL (resolution)

*Smernica:* Accept the proposal and confirm the next step. Calmer tone.

*Vanila rečenica:* All right, that sounds fair. Let us do that.

- **1 – calm** (1): All right, that sounds fair. Let us do that.
- **2 – dissatisfied** (1): All right, that sounds fair. Let's do that. I am not happy about this.

### CONFIRM_AGREEMENT (resolution)

*Smernica:* Repeat in one sentence that you have a plan and say you expect it to happen.

*Vanila rečenica:* All right. So we have a plan for Luka's math grade.

- **1 – calm** (1): All right. So we have a plan for Luka's math grade.
- **2 – dissatisfied** (2): All right. So we have a plan for Luka's math grade. I am not happy about this.
- **3 – angry** (3): All right. So we have a plan for Luka's math grade. And I expect you to keep your word!
- **4 – very angry** (3): All right. So we have a plan for Luka's math grade! This is outrageous! Don't make me call again!

### REDIRECT_TO_TOPIC (discussion)

*Smernica:* The teacher talked about something else. Bring the conversation back to Luka's math grade.

*Vanila rečenica:* I did not call to talk about that. I am calling about Luka's math grade.

- **1 – calm** (1): I did not call to talk about that. I am calling about Luka's math grade.
- **2 – dissatisfied** (2): I did not call to talk about that. I am calling about Luka's math grade. I am not happy about this.
- **3 – angry** (3): I did NOT call to talk about that. I am calling about Luka's math grade. Don't change the subject!
- **4 – very angry** (4): I did NOT call to talk about that. I am calling about Luka's math grade! Stop dodging the question!
- **5 – about to hang up** (5): I did NOT call to talk about that. I am calling about Luka's math grade! I have had enough! Don't you dare change the subject!

### THREATEN_ESCALATION (discussion)

*Smernica:* Say that you will talk to the principal about this if this is not solved. Short and final.

*Vanila rečenica:* If this is not solved, I will talk to the principal about this.

- **4 – very angry** (4): Look, if this is not solved, I will talk to the principal about this! I mean it.
- **5 – about to hang up** (4): No. Listen to me. If this is not solved, I will talk to the principal about this! And I mean tomorrow morning!

### CLOSE_CALL (closing)

*Smernica:* Thank the teacher and confirm the agreed next step.

*Vanila rečenica:* Thank you for listening. I will see you at the meeting.

- **1 – calm** (1): Thank you for listening. I will see you at the meeting.
- **2 – dissatisfied** (1): Thank you for listening. I will see you at the meeting. I expected better.

### END_UNRESOLVED (closing)

*Smernica:* Say you have to go and that the problem is not solved.

*Vanila rečenica:* I have to go now, but this is not over. We still have not solved the grade.

- **2 – dissatisfied** (3): I have to go now, but this is not over. We still have not solved the grade. I expected better.
- **3 – angry** (3): I have to go now, but this is not over. We still have not solved the grade. This makes no sense!
- **4 – very angry** (4): I have to go now, but this is not over. We still have not solved the grade! This was a waste of my time!
- **5 – about to hang up** (5): I have to go NOW, but this is not over. We still have not solved the grade! This is a disgrace! You will hear from the principal!

### HANG_UP (closing)

*Smernica:* End the call abruptly. One or two short sentences.

*Vanila rečenica:* I have nothing more to say. I will talk to the principal about this.

- **4 – very angry** (4): I have nothing more to say. I will talk to the principal about this! This is outrageous! You will hear from me. Goodbye!
- **5 – about to hang up** (5): No. Listen to me. I have NOTHING more to say. I will talk to the principal about this! You will hear from the principal! Goodbye!

## trip_exclusion

### OPEN_COMPLAINT (opening)

*Smernica:* Say who you are and why you are calling. State the main complaint. Do not ask questions yet.

*Vanila rečenica:* Hello, this is Mrs. Jovanovic, Mila's mother. I am calling about Mila not being allowed to go on the class trip. I think keeping Mila from the trip is not fair.

- **1 – calm** (1): Hello, this is Mrs. Jovanovic, Mila's mother. I am calling about Mila not being allowed to go on the class trip. I think keeping Mila from the trip is not fair.
- **2 – dissatisfied** (2): Hello, this is Mrs. Jovanovic, Mila's mother. I am calling about Mila not being allowed to go on the class trip. Keeping Mila from the trip is not fair. I expected a call from the school first.
- **3 – angry** (3): Hello, this is Mrs. Jovanovic, Mila's mother. I am calling about Mila not being allowed to go on the class trip. Keeping Mila from the trip is completely unfair. This makes no sense!
- **4 – very angry** (4): Hello, this is Mrs. Jovanovic, Mila's mother. I am calling about Mila not being allowed to go on the class trip. Keeping Mila from the trip is absolutely unfair! This is ridiculous!
- **5 – about to hang up** (5): Hello, this is Mrs. Jovanovic, Mila's mother. I am calling about Mila not being allowed to go on the class trip. Keeping Mila from the trip is absolutely unfair! I am sick and tired of this! I want answers right NOW!

### ELABORATE_COMPLAINT (complaint)

*Smernica:* Answer what the teacher asked. Add exactly one new fact: Mila has been looking forward to this trip for months. Keep the main complaint.

*Vanila rečenica:* Mila has been looking forward to this trip for months. So I would like to understand how this happened.

- **1 – calm** (1): Mila has been looking forward to this trip for months. So I would like to understand how this happened.
- **2 – dissatisfied** (2): Mila has been looking forward to this trip for months. So I want to understand how this happened. Frankly, this is disappointing.
- **3 – angry** (2): Mila has been looking forward to this trip for months. So I want to understand how this happened. This is unacceptable!
- **4 – very angry** (4): Look, Mila has been looking forward to this trip for months. So I want to understand how this happened! Do you even check these things properly?
- **5 – about to hang up** (5): Mila has been looking forward to this trip for months. So I want to understand how this happened! This is a disgrace! Explain it to me, right NOW!

### RAISE_COMPLAINT (complaint)

*Smernica:* Bring up the next problem in one or two sentences: Nobody from the school told me about the notes. I heard about the trip decision from Mila, the day before.

*Vanila rečenica:* And there is something else. Nobody from the school told me about the notes. I heard about the trip decision from Mila, the day before.

- **1 – calm** (1): And there is something else. Nobody from the school told me about the notes. I heard about the trip decision from Mila, the day before.
- **2 – dissatisfied** (2): And there is something else. Nobody from the school told me about the notes. I heard about the trip decision from Mila, the day before. That is not how it should work.
- **3 – angry** (3): And there is something else. Nobody from the school told me about the notes. I heard about the trip decision from Mila, the day before. I am really angry about this!
- **4 – very angry** (4): And there is something else. NOBODY from the school told me about the notes. I heard about the trip decision from Mila, the day before! Do you even care about your students?
- **5 – about to hang up** (4): Enough. And there is something else. NOBODY from the school told me about the notes. I heard about the trip decision from Mila, the day before! Unbelievable!

### REVEAL_HIDDEN_NEED (discussion)

*Smernica:* Say what really worries you: I am afraid the school now sees Mila as a problem child. One or two sentences. This is a softer moment.

*Vanila rečenica:* Honestly, I am worried. I am afraid the school now sees Mila as a problem child.

- **1 – calm** (1): Honestly, I am worried. I am afraid the school now sees Mila as a problem child.
- **2 – dissatisfied** (2): Honestly, I am worried. I am afraid the school now sees Mila as a problem child. I expected better.
- **3 – angry** (3): Honestly, I am really worried. I am afraid the school now sees Mila as a problem child. This makes no sense!

### ACKNOWLEDGE_PARTIALLY (discussion)

*Smernica:* Accept that the teacher understood you, but say that the problem is still there.

*Vanila rečenica:* Well, at least you see my point. But the trip decision is still a problem.

- **1 – calm** (2): Well, at least you see my point. But the trip decision is still a problem.
- **2 – dissatisfied** (3): Well, at least you see my point. But the trip decision is still a problem. Frankly, this is disappointing.
- **3 – angry** (3): Well, at least you see my point. But the trip decision is still a huge problem. This makes no sense!
- **4 – very angry** (4): Well, at least you see my point. But the trip decision is still a huge problem! Don't think nice words will fix this!

### REPEAT_COMPLAINT (discussion)

*Smernica:* Say that the teacher did not answer you and repeat the main complaint.

*Vanila rečenica:* You are not answering me. I said that keeping Mila from the trip is not fair.

- **2 – dissatisfied** (2): You are not answering me. I said that keeping Mila from the trip is not fair. I will say it again.
- **3 – angry** (3): You are not answering me. I said that keeping Mila from the trip is completely unfair. I am really angry about this!
- **4 – very angry** (4): You are not answering me. I said that keeping Mila from the trip is absolutely unfair! This is ridiculous! I have said it three times already!
- **5 – about to hang up** (5): No. Listen to me. You are not answering me. I said that keeping Mila from the trip is absolutely UNFAIR! I am done repeating myself!

### DEMAND_ACTION (discussion)

*Smernica:* Demand a concrete action: let Mila go on the trip or explain the decision in a meeting.

*Vanila rečenica:* I would like you to let Mila go on the trip or explain the decision in a meeting.

- **3 – angry** (3): I demand that you let Mila go on the trip or explain the decision in a meeting. And I want it this week!
- **4 – very angry** (4): I demand that you let Mila go on the trip or explain the decision in a meeting! Do you even care about your students?
- **5 – about to hang up** (5): I demand that you let Mila go on the trip or explain the decision in a meeting! I have had ENOUGH!

### REJECT_RULES (discussion)

*Smernica:* The teacher hides behind the rules. Say that the rules do not solve your problem.

*Vanila rečenica:* I understand that there are rules, but the rules do not help Mila.

- **3 – angry** (2): I understand that there are rules, but the rules don't help Mila. This is unacceptable!
- **4 – very angry** (4): I understand that there are rules, but the rules don't help Mila! This is outrageous! Stop hiding behind the rules!
- **5 – about to hang up** (5): I understand that there are rules, but the rules don't help Mila! I have had ENOUGH! I don't want excuses, I want a solution!

### REJECT_EXPLANATION (discussion)

*Smernica:* The teacher gives facts while you are still angry. Say that the facts do not answer your complaint.

*Vanila rečenica:* That explanation does not help Mila at all.

- **3 – angry** (3): That explanation does nothing to help Mila at all. I am really angry about this!
- **4 – very angry** (4): That explanation does nothing to help Mila at all! Do you even care about your students? Don't lecture me!
- **5 – about to hang up** (5): That explanation does nothing to help Mila at all! I have had ENOUGH! I don't want excuses, I want a solution!

### ACCUSE (discussion)

*Smernica:* Blame the teacher for the problem and for the lack of communication. No new facts.

*Vanila rečenica:* I think the school did not do its job here. Nobody told me that Mila was struggling.

- **3 – angry** (3): The school did not do its job here. Nobody told me that Mila was struggling. This is unacceptable!
- **4 – very angry** (4): The school completely failed here. NOBODY told me that Mila was struggling! Do you even care about your students?
- **5 – about to hang up** (5): The school completely failed here. NOBODY told me that Mila was struggling! I am sick and tired of this! What kind of teacher does that?

### REJECT_PROPOSAL (discussion)

*Smernica:* Reject the teacher's proposal. Say that first you want an answer about the main complaint.

*Vanila rečenica:* That does not solve the problem for me yet. First I want an answer about the trip decision.

- **3 – angry** (3): That doesn't solve the problem for me yet. First I want an answer about the trip decision. This makes no sense!
- **4 – very angry** (4): That doesn't solve the problem for me yet. First I want an answer about the trip decision! This is ridiculous! You think that fixes everything?
- **5 – about to hang up** (5): That doesn't solve the problem for me yet. First I want an answer about the trip decision! I have had ENOUGH! Don't insult me with that!

### ASK_FOR_PLAN (resolution)

*Smernica:* Ask what exactly the teacher is going to do about the problem.

*Vanila rečenica:* So what exactly are you going to do about the trip decision?

- **1 – calm** (1): So what exactly are you going to do about the trip decision?
- **2 – dissatisfied** (2): So what exactly are you going to do about the trip decision? Frankly, this is disappointing.
- **3 – angry** (2): So what exactly are you going to do about the trip decision? This is unacceptable!
- **4 – very angry** (4): So what exactly are you going to do about the trip decision? This is outrageous! Well? I am waiting!

### CONDITIONAL_ACCEPT (resolution)

*Smernica:* Accept the teacher's proposal, but add one condition: you to tell me about behaviour notes when they happen.

*Vanila rečenica:* That could work. But I also want you to tell me about behaviour notes when they happen.

- **1 – calm** (1): That could work. But I also want you to tell me about behaviour notes when they happen.
- **2 – dissatisfied** (2): That could work. But I also want you to tell me about behaviour notes when they happen. And I will hold you to that.
- **3 – angry** (2): That could work. But I also want you to tell me about behaviour notes when they happen. This makes no sense!

### ACCEPT_PROPOSAL (resolution)

*Smernica:* Accept the proposal and confirm the next step. Calmer tone.

*Vanila rečenica:* All right, that sounds fair. Let us do that.

- **1 – calm** (1): All right, that sounds fair. Let us do that.
- **2 – dissatisfied** (1): All right, that sounds fair. Let's do that. I am not happy about this.

### CONFIRM_AGREEMENT (resolution)

*Smernica:* Repeat in one sentence that you have a plan and say you expect it to happen.

*Vanila rečenica:* All right. So we have a plan for Mila and the class trip.

- **1 – calm** (1): All right. So we have a plan for Mila and the class trip.
- **2 – dissatisfied** (2): All right. So we have a plan for Mila and the class trip. I am not happy about this.
- **3 – angry** (3): All right. So we have a plan for Mila and the class trip. And I expect you to keep your word!
- **4 – very angry** (3): All right. So we have a plan for Mila and the class trip! This is outrageous! Don't make me call again!

### REDIRECT_TO_TOPIC (discussion)

*Smernica:* The teacher talked about something else. Bring the conversation back to Mila and the class trip.

*Vanila rečenica:* I did not call to talk about that. I am calling about Mila and the class trip.

- **1 – calm** (1): I did not call to talk about that. I am calling about Mila and the class trip.
- **2 – dissatisfied** (2): I did not call to talk about that. I am calling about Mila and the class trip. I am not happy about this.
- **3 – angry** (3): I did NOT call to talk about that. I am calling about Mila and the class trip. Don't change the subject!
- **4 – very angry** (4): I did NOT call to talk about that. I am calling about Mila and the class trip! Stop dodging the question!
- **5 – about to hang up** (5): I did NOT call to talk about that. I am calling about Mila and the class trip! I have had enough! Don't you dare change the subject!

### THREATEN_ESCALATION (discussion)

*Smernica:* Say that you will talk to the principal about this if this is not solved. Short and final.

*Vanila rečenica:* If this is not solved, I will talk to the principal about this.

- **4 – very angry** (4): Look, if this is not solved, I will talk to the principal about this! I mean it.
- **5 – about to hang up** (4): No. Listen to me. If this is not solved, I will talk to the principal about this! And I mean tomorrow morning!

### CLOSE_CALL (closing)

*Smernica:* Thank the teacher and confirm the agreed next step.

*Vanila rečenica:* Thank you for listening. I will see you at the meeting.

- **1 – calm** (1): Thank you for listening. I will see you at the meeting.
- **2 – dissatisfied** (1): Thank you for listening. I will see you at the meeting. I expected better.

### END_UNRESOLVED (closing)

*Smernica:* Say you have to go and that the problem is not solved.

*Vanila rečenica:* I have to go now, but this is not over. We still have not solved the trip decision.

- **2 – dissatisfied** (3): I have to go now, but this is not over. We still have not solved the trip decision. I expected better.
- **3 – angry** (3): I have to go now, but this is not over. We still have not solved the trip decision. This makes no sense!
- **4 – very angry** (4): I have to go now, but this is not over. We still have not solved the trip decision! This was a waste of my time!
- **5 – about to hang up** (5): I have to go NOW, but this is not over. We still have not solved the trip decision! This is a disgrace! You will hear from the principal!

### HANG_UP (closing)

*Smernica:* End the call abruptly. One or two short sentences.

*Vanila rečenica:* I have nothing more to say. I will talk to the principal about this.

- **4 – very angry** (4): I have nothing more to say. I will talk to the principal about this! This is outrageous! You will hear from me. Goodbye!
- **5 – about to hang up** (5): No. Listen to me. I have NOTHING more to say. I will talk to the principal about this! You will hear from the principal! Goodbye!
