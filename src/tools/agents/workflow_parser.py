"""
Workflow parser for OpenAI Agent structured prompts.

This module provides utilities to parse and structure complex troubleshooting
workflows into a format that's easier for AI agents to understand and execute.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class WorkflowStep:
    """Represents a single step in a troubleshooting workflow."""
    phase: str
    step_id: str
    title: str
    objective: str
    agent_role: Optional[str] = None
    search_queries: List[Dict[str, Any]] = None
    resource_references: List[str] = None
    dependencies: List[str] = None
    parallel_execution: bool = False
    
    def __post_init__(self):
        if self.search_queries is None:
            self.search_queries = []
        if self.resource_references is None:
            self.resource_references = []
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class WorkflowPhase:
    """Represents a phase containing multiple steps."""
    phase_id: str
    title: str
    description: str
    steps: List[WorkflowStep] = None
    
    def __post_init__(self):
        if self.steps is None:
            self.steps = []


@dataclass
class ParsedWorkflow:
    """Represents a complete parsed workflow."""
    title: str
    description: str
    methodology: str
    phases: List[WorkflowPhase] = None
    decision_matrix: Dict[str, Any] = None
    remediation_strategies: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.phases is None:
            self.phases = []
        if self.decision_matrix is None:
            self.decision_matrix = {}
        if self.remediation_strategies is None:
            self.remediation_strategies = {}


class WorkflowParser:
    """Parser for structured troubleshooting workflow prompts."""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.WorkflowParser")
    
    def parse_workflow(self, prompt_content: str) -> ParsedWorkflow:
        """Parse a workflow prompt into structured components."""
        try:
            # Extract title and description
            title = self._extract_title(prompt_content)
            description = self._extract_description(prompt_content)
            methodology = self._extract_methodology(prompt_content)
            
            # Extract phases and steps
            phases = self._extract_phases(prompt_content)
            
            # Extract decision matrix and remediation strategies
            decision_matrix = self._extract_decision_matrix(prompt_content)
            remediation_strategies = self._extract_remediation_strategies(prompt_content)
            
            workflow = ParsedWorkflow(
                title=title,
                description=description,
                methodology=methodology,
                phases=phases,
                decision_matrix=decision_matrix,
                remediation_strategies=remediation_strategies
            )
            
            self.logger.info(f"Parsed workflow: {len(phases)} phases, {sum(len(p.steps) for p in phases)} total steps")
            return workflow
            
        except Exception as e:
            self.logger.error(f"Error parsing workflow: {e}")
            # Return a basic workflow structure
            return ParsedWorkflow(
                title="Troubleshooting Workflow",
                description="Structured troubleshooting workflow",
                methodology="Systematic analysis"
            )
    
    def _extract_title(self, content: str) -> str:
        """Extract the main title from the content."""
        # Look for the first H1 heading
        title_match = re.search(r'^#\s+(.+)', content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()
        return "Troubleshooting Workflow"
    
    def _extract_description(self, content: str) -> str:
        """Extract the workflow description."""
        # Look for content between title and first phase
        desc_match = re.search(r'#{1}\s+.+?\n\n(.+?)(?=#{2}|$)', content, re.DOTALL)
        if desc_match:
            return desc_match.group(1).strip()[:500]  # Limit length
        return "Structured troubleshooting workflow"
    
    def _extract_methodology(self, content: str) -> str:
        """Extract methodology information."""
        # Look for OODA or methodology sections
        method_patterns = [
            r'OODA Loop.*?\n(.+?)(?=#{2}|---)',
            r'Methodology.*?\n(.+?)(?=#{2}|---)',
            r'Diagnostic Philosophy.*?\n(.+?)(?=#{2}|---)'
        ]
        
        for pattern in method_patterns:
            match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()[:300]
        
        return "Observe-Orient-Decide-Act (OODA) methodology"
    
    def _extract_phases(self, content: str) -> List[WorkflowPhase]:
        """Extract phases and their steps from the content."""
        phases = []
        
        # Find all phase sections (## Phase X:)
        phase_pattern = r'#{2}\s+(Phase\s+\d+.*?)\n(.*?)(?=#{2}\s+Phase|\Z)'
        phase_matches = re.findall(phase_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for phase_title, phase_content in phase_matches:
            phase_id = self._extract_phase_id(phase_title)
            steps = self._extract_steps(phase_content)
            
            phase = WorkflowPhase(
                phase_id=phase_id,
                title=phase_title.strip(),
                description=self._extract_phase_description(phase_content),
                steps=steps
            )
            phases.append(phase)
        
        return phases
    
    def _extract_phase_id(self, phase_title: str) -> str:
        """Extract phase ID from title."""
        # Extract number from "Phase X:" format
        match = re.search(r'Phase\s+(\d+)', phase_title, re.IGNORECASE)
        if match:
            return f"phase_{match.group(1)}"
        return f"phase_{len(phase_title)}"  # Fallback
    
    def _extract_phase_description(self, phase_content: str) -> str:
        """Extract phase description."""
        # Get first paragraph after phase title
        lines = phase_content.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('**'):
                return line[:200]
        return "Phase description"
    
    def _extract_steps(self, phase_content: str) -> List[WorkflowStep]:
        """Extract steps from phase content."""
        steps = []
        
        # Find step sections (### Step X.X:)
        step_pattern = r'#{3,4}\s+(Step\s+[\d.]+.*?)\n(.*?)(?=#{3,4}\s+Step|\Z)'
        step_matches = re.findall(step_pattern, phase_content, re.DOTALL | re.IGNORECASE)
        
        for step_title, step_content in step_matches:
            step = self._parse_step(step_title, step_content)
            if step:
                steps.append(step)
        
        return steps
    
    def _parse_step(self, step_title: str, step_content: str) -> Optional[WorkflowStep]:
        """Parse a single step from its content."""
        try:
            # Extract step ID
            step_id_match = re.search(r'Step\s+([\d.]+)', step_title, re.IGNORECASE)
            step_id = step_id_match.group(1) if step_id_match else "unknown"
            
            # Extract objective
            objective = self._extract_objective(step_content)
            
            # Extract agent role
            agent_role = self._extract_agent_role(step_content)
            
            # Extract search queries
            search_queries = self._extract_search_queries(step_content)
            
            # Extract resource references
            resource_references = self._extract_resource_references(step_content)
            
            # Determine if parallel execution
            parallel_execution = "simultaneously" in step_content.lower() or "parallel" in step_content.lower()
            
            return WorkflowStep(
                phase="extracted",
                step_id=step_id,
                title=step_title.strip(),
                objective=objective,
                agent_role=agent_role,
                search_queries=search_queries,
                resource_references=resource_references,
                parallel_execution=parallel_execution
            )
            
        except Exception as e:
            self.logger.error(f"Error parsing step '{step_title}': {e}")
            return None
    
    def _extract_objective(self, content: str) -> str:
        """Extract the objective from step content."""
        # Look for "Objective:" sections
        obj_match = re.search(r'Objective[:\s]+(.+?)(?=\n|$)', content, re.IGNORECASE)
        if obj_match:
            return obj_match.group(1).strip()
        
        # Fallback: use first sentence
        sentences = content.split('.')
        if sentences:
            return sentences[0].strip()[:200]
        
        return "Execute step analysis"
    
    def _extract_agent_role(self, content: str) -> Optional[str]:
        """Extract agent role if specified."""
        role_match = re.search(r'Agent[:\s]+(.+?)(?=\n|$)', content, re.IGNORECASE)
        if role_match:
            return role_match.group(1).strip()
        return None
    
    def _extract_search_queries(self, content: str) -> List[Dict[str, Any]]:
        """Extract search queries from JSON blocks."""
        queries = []
        
        # Find JSON blocks with search queries
        json_pattern = r'```json\s*\n(.*?)\n```'
        json_matches = re.findall(json_pattern, content, re.DOTALL)
        
        for json_str in json_matches:
            try:
                query_data = json.loads(json_str)
                if isinstance(query_data, dict) and "method" in query_data:
                    queries.append(query_data)
            except json.JSONDecodeError:
                self.logger.debug(f"Failed to parse JSON: {json_str[:100]}...")
        
        return queries
    
    def _extract_resource_references(self, content: str) -> List[str]:
        """Extract resource URI references."""
        uris = []
        
        # Pattern to match resource URIs
        uri_patterns = [
            r'"uri":\s*"([^"]+)"',
            r'(splunk-docs://[^\s\]]+)',
            r'(splunk://[^\s\]]+)',
            r'(resource://[^\s\]]+)'
        ]
        
        for pattern in uri_patterns:
            matches = re.findall(pattern, content)
            uris.extend(matches)
        
        # Remove duplicates
        return list(set(uris))
    
    def _extract_decision_matrix(self, content: str) -> Dict[str, Any]:
        """Extract decision matrix information."""
        matrix = {}
        
        # Look for decision matrix sections
        matrix_section = re.search(
            r'Decision Matrix.*?\n(.*?)(?=#{2}|---|\Z)', 
            content, 
            re.DOTALL | re.IGNORECASE
        )
        
        if matrix_section:
            matrix_content = matrix_section.group(1)
            
            # Extract indicators by color/severity
            indicators = {
                "healthy": self._extract_indicators(matrix_content, "🟢|Healthy|GREEN"),
                "warning": self._extract_indicators(matrix_content, "🟡|Warning|YELLOW"),
                "critical": self._extract_indicators(matrix_content, "🔴|Critical|RED")
            }
            
            matrix["indicators"] = indicators
        
        return matrix
    
    def _extract_indicators(self, content: str, pattern: str) -> List[str]:
        """Extract indicators for a specific severity level."""
        indicators = []
        
        # Find section matching the pattern
        section_match = re.search(
            f'({pattern}).*?\n(.*?)(?=🟢|🟡|🔴|#{2}|\Z)', 
            content, 
            re.DOTALL | re.IGNORECASE
        )
        
        if section_match:
            section_content = section_match.group(2)
            # Extract bullet points
            bullet_matches = re.findall(r'[-*]\s+(.+)', section_content)
            indicators.extend([match.strip() for match in bullet_matches])
        
        return indicators
    
    def _extract_remediation_strategies(self, content: str) -> Dict[str, Any]:
        """Extract remediation strategies."""
        strategies = {}
        
        # Look for remediation section
        remediation_section = re.search(
            r'Remediation.*?\n(.*?)(?=#{2}|---|\Z)', 
            content, 
            re.DOTALL | re.IGNORECASE
        )
        
        if remediation_section:
            remediation_content = remediation_section.group(1)
            
            # Extract strategy categories
            strategy_pattern = r'\*\*(.+?)\*\*.*?→.*?\n(.*?)(?=\*\*|\Z)'
            strategy_matches = re.findall(strategy_pattern, remediation_content, re.DOTALL)
            
            for category, actions in strategy_matches:
                action_list = re.findall(r'[-*]\s+(.+)', actions)
                strategies[category.strip()] = [action.strip() for action in action_list]
        
        return strategies
    
    def generate_structured_prompt(self, workflow: ParsedWorkflow) -> str:
        """Generate a structured prompt from parsed workflow."""
        prompt = f"""# {workflow.title}

## Workflow Overview
{workflow.description}

## Methodology
{workflow.methodology}

## Execution Plan
"""
        
        for phase in workflow.phases:
            prompt += f"\n### {phase.title}\n{phase.description}\n"
            
            for step in phase.steps:
                prompt += f"\n#### {step.title}\n"
                prompt += f"**Objective**: {step.objective}\n"
                
                if step.agent_role:
                    prompt += f"**Agent Role**: {step.agent_role}\n"
                
                if step.parallel_execution:
                    prompt += f"**Execution**: Parallel execution recommended\n"
                
                if step.search_queries:
                    prompt += f"**Queries**: {len(step.search_queries)} search operations\n"
                
                if step.resource_references:
                    prompt += f"**Resources**: {', '.join(step.resource_references[:3])}{'...' if len(step.resource_references) > 3 else ''}\n"
        
        # Add decision matrix
        if workflow.decision_matrix:
            prompt += f"\n## Decision Matrix\n"
            for severity, indicators in workflow.decision_matrix.get("indicators", {}).items():
                if indicators:
                    prompt += f"\n**{severity.title()} Indicators**:\n"
                    for indicator in indicators[:5]:  # Limit to 5 per category
                        prompt += f"- {indicator}\n"
        
        # Add remediation strategies
        if workflow.remediation_strategies:
            prompt += f"\n## Remediation Strategies\n"
            for category, actions in workflow.remediation_strategies.items():
                if actions:
                    prompt += f"\n**{category}**:\n"
                    for action in actions[:3]:  # Limit to 3 per category
                        prompt += f"- {action}\n"
        
        return prompt
    
    def to_json(self, workflow: ParsedWorkflow) -> str:
        """Convert workflow to JSON representation."""
        return json.dumps(asdict(workflow), indent=2, default=str) 