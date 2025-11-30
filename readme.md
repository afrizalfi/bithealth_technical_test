Code Quality & Design Principles: Onboarding Exercise 
Overview 

This repository contains a functional but intentionally unstructured implementation integrating FastAPI, LangGraph, and Qdrant. The codebase serves as a practical exercise to evaluate and strengthen your software design instincts. 

While the application works as intended, it deliberately omits key engineering practices we value highly: encapsulation, separation of concerns, testability, and maintainability. Your task is not to fix it immediately—but to analyze, understand the trade-offs, and plan a path toward a robust, production-grade architecture. 

This exercise mirrors real-world scenarios where technical debt accumulates under pressure, and clean design must be reintroduced thoughtfully. 
 
What to Observe 

As you review the code, consider the following dimensions: 
1. State and Scope 

    How is application state managed?
    Are dependencies explicit or implicit?
    What risks arise from shared global state in a concurrent environment?
     
2. OOP, Modularity, and Cohesion 

    Are related responsibilities grouped logically?
    Can components be understood, tested, or replaced in isolation?
    Where do you see duplicated or tightly coupled logic?
     
3. Extensibility and Change 

    How would you add a new embedding model?
    What would happen if the vector database changed?
    Which parts of the code would require the most careful regression testing after a small change?
     
4. Testability 

    Can individual units of behavior be validated without bootstrapping the entire application?
    Are side effects (e.g., database calls) isolated and mockable?
     

5. Configuration and Environment Sensitivity 

    Are environment-specific values hardcoded?
    How would this behave in staging vs. production?
     
Our Engineering Expectations 

At our team, we believe that clarity is a feature. We prioritize: 

    Explicit over implicit: Dependencies should be declared, not assumed.
    Composition over global access: Services should collaborate through well-defined interfaces.
    Single responsibility: Each module, class, or function should have one clear purpose.
    Defensive yet readable code: Errors should be handled gracefully, but not at the cost of understandability.
    Design for change: Systems should accommodate evolution without cascading rewrites.
     
This doesn’t mean over-engineering, but it does mean resisting shortcuts that create long-term friction. 
 
Your Next Steps 

    Spend time reading the current implementation. Run it. Break it. Observe its behavior.
    Document your findings: What design smells do you notice? What would you prioritize refactoring first—and why?
    Propose a migration strategy: How would you incrementally improve the architecture without breaking functionality? Consider:
        Introducing interfaces for external services
        Decoupling web logic from business logic
        Centralizing configuration
        Enabling unit and integration testing
 
Final Note 
This code isn’t a failure, it’s a starting point. Every system begins somewhere. Our job as engineers is to recognize when a design no longer serves its purpose and to evolve it with intention. 

We look forward to seeing how you’d guide this code toward clarity, resilience, and maintainability. 