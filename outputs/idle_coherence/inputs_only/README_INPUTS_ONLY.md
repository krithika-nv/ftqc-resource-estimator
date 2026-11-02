# Published-coherence / hypothetical controller-delay INPUT PREVIEW

> This is NOT a decoded QEC result. NO logical failure rates or feasibility decisions are generated here.

**Source:** Google Quantum AI and Collaborators, Nature 638, 920–926 (2025), mean Willow T1=68 us, T2,CPMG=89 us, QEC cycle=1.1 us. T2,CPMG is NOT idle Ramsey T2 and is used only as a sensitivity proxy.
**Classification:** measured published means are T1, T2_CPMG and the cycle time; controller readout-channel counts, batching, per-channel timing and power are NOT Willow measurements.
**Model:** Readout waves per round = ceil(4(d²−1)/channels). Extra data idle = max(0, batches × assumed readout-slot − 1.1us). Insert a Pauli-twirled exponential T1/T2 channel on data qubits at each of d syndrome-round starts.
**Warning:** Pauli twirling omits the non-unital part of amplitude damping. CPMG coherence is not free-idle Ramsey T2. Measurement queuing assumes time can be reallocated without modifying the stabilizer circuit; this is not established.
**Distinct question:** The calibrated device metric is not yet a calibrated controller-delay model. Only real Stim/PyMatching simulation can test the hypothetical delayed schedules.

| d | Scenario | Batches | Extra idle / round (us) | Added data Pauli probability / round |
|---:|---|---:|---:|---:|
| 3 | wide_parallel_readout | 1 | 0.0000 | 0.000000 |
| 3 | medium_parallel_readout | 1 | 0.0000 | 0.000000 |
| 3 | constrained_parallel_readout | 1 | 0.0000 | 0.000000 |
| 5 | wide_parallel_readout | 1 | 0.0000 | 0.000000 |
| 5 | medium_parallel_readout | 1 | 0.0000 | 0.000000 |
| 5 | constrained_parallel_readout | 3 | 0.2500 | 0.002320 |
| 7 | wide_parallel_readout | 1 | 0.0000 | 0.000000 |
| 7 | medium_parallel_readout | 2 | 0.0000 | 0.000000 |
| 7 | constrained_parallel_readout | 6 | 1.6000 | 0.014722 |
| 9 | wide_parallel_readout | 2 | 0.0000 | 0.000000 |
| 9 | medium_parallel_readout | 3 | 0.2500 | 0.002320 |
| 9 | constrained_parallel_readout | 10 | 3.4000 | 0.030934 |
