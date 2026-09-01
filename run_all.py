"""
Master orchestration script for the Quantum Workforce Optimizer pipeline.
This script runs data generation, AI demand forecasting, classical optimization,
shift mapping, quantum simulation, and queue validation sequentially.
"""
import os
import sys

# Ensure backend is in sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

def main():
    print("==================================================")
    print("STARTING QUANTUM WORKFORCE OPTIMIZATION PIPELINE")
    print("==================================================")
    
    # 1. Data Generation
    print("\n--- STEP 1: Running Data Generation ---")
    from app.core_engine.common.data_generator import generate_data
    generate_data()
    print("Data generation completed successfully.")
    
    # 2. Demand Forecasting
    print("\n--- STEP 2: Running AI Demand Forecasting ---")
    from app.core_engine.forecasting.demand_forecaster import train_forecast
    train_forecast()
    print("AI demand forecasting completed successfully.")
    
    # 3. Classical Optimization
    print("\n--- STEP 3: Running Classical Optimization ---")
    from app.core_engine.optimization.classical_optimizer import run_classical_optimization
    run_classical_optimization()
    print("Classical optimization completed successfully.")
    
    # 4. Shift Optimization
    print("\n--- STEP 4: Running Shift Optimization ---")
    from app.core_engine.optimization.shift_optimizer import run_shift_optimization
    run_shift_optimization()
    print("Shift optimization completed successfully.")
    
    # 5. Quantum Optimization
    print("\n--- STEP 5: Running Quantum Optimization ---")
    from app.core_engine.quantum.quantum_optimizer import run_quantum_optimization
    run_quantum_optimization()
    print("Quantum optimization completed successfully.")
    
    # 6. Queue Validation
    print("\n--- STEP 6: Running Queue Simulation (Erlang C) ---")
    from app.core_engine.queue.queue_simulator import run_queue_simulation
    run_queue_simulation()
    print("Queue validation completed successfully.")
    
    print("\n==================================================")
    print("PIPELINE COMPLETED SUCCESSFULLY!")
    print("All outputs generated in 'data/', 'models/', and 'results/' directories.")
    print("To launch the dashboard, run: streamlit run src/dashboard.py")
    print("==================================================")

if __name__ == "__main__":
    main()
