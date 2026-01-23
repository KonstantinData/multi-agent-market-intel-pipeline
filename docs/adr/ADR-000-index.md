# Architecture Decision Records (ADR) Index

This document provides an index of all architectural decisions made for the multi-agent market intelligence pipeline.

## ADR Status Legend

- **PROPOSED**: Decision under consideration
- **ACCEPTED**: Decision approved and implemented
- **DEPRECATED**: Decision superseded by newer ADR
- **REJECTED**: Decision considered but not adopted

## Decision Records

### ADR-001: Parallel Fan-Out/Fan-In Architecture
**Status**: ACCEPTED  
**Date**: November 2024  
**Summary**: Implement parallel domain agents with explicit merge barriers to enable concurrent processing while maintaining data consistency.

### ADR-002: Contract-Gated Validation
**Status**: ACCEPTED  
**Date**: November 2024  
**Summary**: Enforce strict output contracts at each pipeline step with hard-fail validation to ensure data quality and governance compliance.

### ADR-003: Central Entity Registry and ID Policy
**Status**: ACCEPTED  
**Date**: November 2024  
**Summary**: Implement centralized entity deduplication and deterministic ID allocation (TGT-001, MFR-001, CUS-001) to prevent ID collisions and ensure referential integrity.

### ADR-004: Run Artifact Model
**Status**: ACCEPTED  
**Date**: November 2024  
**Summary**: Establish comprehensive artifact-based reproducibility with structured run directories for debugging, audit trails, and governance compliance.

### ADR-005: Cross-Reference System Implementation
**Status**: ACCEPTED  
**Date**: December 2024  
**Summary**: Implement comprehensive cross-reference system with graph-based relationship management, multi-level validation, and rich export capabilities to ensure referential integrity and enable relationship analysis.

## Decision Categories

### Infrastructure Decisions
- ADR-001: Parallel Fan-Out/Fan-In Architecture
- ADR-004: Run Artifact Model
- ADR-005: Cross-Reference System Implementation

### Data Quality & Governance
- ADR-002: Contract-Gated Validation
- ADR-003: Central Entity Registry and ID Policy
- ADR-005: Cross-Reference System Implementation

### System Architecture
- ADR-001: Parallel Fan-Out/Fan-In Architecture
- ADR-003: Central Entity Registry and ID Policy
- ADR-005: Cross-Reference System Implementation

## Cross-References Between ADRs

### ADR Dependencies
- **ADR-005** depends on **ADR-003** (Entity Registry) for entity ID management
- **ADR-005** depends on **ADR-002** (Contract Validation) for validation framework
- **ADR-005** depends on **ADR-001** (Parallel Architecture) for merge barrier integration
- **ADR-005** depends on **ADR-004** (Artifact Model) for export structure

### ADR Interactions
- **ADR-001** and **ADR-005**: Cross-reference validation occurs at merge barriers
- **ADR-002** and **ADR-005**: Cross-reference validation extends contract validation
- **ADR-003** and **ADR-005**: Entity registry provides entities for relationship graph
- **ADR-004** and **ADR-005**: Cross-reference matrices included in run artifacts

## Implementation Status

### Completed (✅)
- ADR-001: Parallel architecture framework
- ADR-002: Contract validation system
- ADR-003: Entity registry and ID allocation
- ADR-004: Artifact directory structure
- ADR-005: Cross-reference system core components

### In Progress (🔄)
- Integration of cross-reference system with orchestrator
- Agent template updates for relations_delta
- Performance optimization for large graphs

### Planned (📋)
- Advanced graph algorithms (centrality, clustering)
- Temporal relationship tracking
- Graph visualization exports

## Review and Update Process

### ADR Lifecycle
1. **Proposal**: New ADR created with PROPOSED status
2. **Review**: Technical review and stakeholder feedback
3. **Decision**: Accept, reject, or request modifications
4. **Implementation**: Approved ADRs implemented and tested
5. **Maintenance**: Periodic review and updates as needed

### Review Schedule
- **Quarterly**: Review all ACCEPTED ADRs for relevance
- **Major Releases**: Comprehensive ADR review and updates
- **As Needed**: Individual ADR updates based on implementation learnings

### Change Management
- ADRs should not be modified after ACCEPTED status
- New ADRs should be created to supersede existing decisions
- DEPRECATED ADRs remain for historical reference
- All changes must maintain backward compatibility where possible

## Contact and Governance

### ADR Ownership
- **Technical Lead**: Overall ADR governance and consistency
- **Architecture Team**: Technical review and approval
- **Product Owner**: Business requirements and priorities
- **Development Team**: Implementation feedback and feasibility

### Decision Authority
- **Infrastructure ADRs**: Technical Lead + Architecture Team
- **Business Logic ADRs**: Product Owner + Technical Lead
- **Implementation ADRs**: Development Team + Technical Lead

For questions about specific ADRs or the decision process, please contact the Technical Lead or create an issue in the project repository.