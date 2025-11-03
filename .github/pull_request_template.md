## Description  
Added Kinesis integration to the Food Delivery project for tracking delivery driver addresses.
This includes creating a dedicated Kinesis Stream for driver location events, a Lambda function to publish location updates to the stream, and a Lambda function to consume and process these events.
Integration tests were added to verify end-to-end message flow from the producer Lambda to the consumer Lambda.

---

## Changes  
[✅] Feature added — Kinesis Stream for driver location events
[✅] Feature added — Lambda function to publish driver location updates 
[✅] Feature added — Lambda function to consume and process driver location events
[✅] Tests — Added integration tests for producer-consumer flow
[ ]Refactor
[ ]Documentation

---

## Checklist  
- [✅] Code follows project guidelines  
- [✅] integration tests added/updated  
- [✅] All tests passing locally  
- [ ] Documentation updated (if needed)  
- [✅] No sensitive data committed  

---

## How to Test  
Steps for reviewers to test this PR:  

