## Description  
Added EventBridge integration to the Food Delivery project for handling restaurant order updates.
This includes creating a dedicated EventBridge event bus for routing order events, a Lambda function to update order status based on incoming events, and logic to publish order update events from the restaurant service.
Integration tests were added to verify event routing and Lambda execution flow. 

---

## Changes  
[✅] Feature added — EventBridge event bus for order updates
[✅] Feature added — Lambda function to update order status
[✅] Feature added — Event publishing for restaurant order updates
[✅] Tests — Added integration tests for event publishing and status update flow
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

