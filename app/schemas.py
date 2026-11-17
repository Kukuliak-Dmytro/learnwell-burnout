"""Request validation and Swagger documentation."""
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator


class StudentFeatures(BaseModel):
    model_config = ConfigDict(extra='forbid')
    major_category: Literal['Arts','Business','Humanities','Medical','STEM'] = Field(description='Спеціальність')
    year_of_study: Literal['Freshman','Sophomore','Junior','Senior','Graduate']
    pre_semester_gpa: float = Field(ge=0, le=4)
    weekly_genai_hours: float = Field(ge=0)
    primary_use_case: Literal[
        'Copywriting/Drafting','Debugging/Troubleshooting',
        'Direct_Answer_Generation','Ideation','Summarizing_Reading'
    ]
    prompt_engineering_skill: Literal['Beginner','Intermediate','Advanced']
    tool_diversity: int = Field(ge=0)
    paid_subscription: bool
    traditional_study_hours: float = Field(ge=0)
    perceived_ai_dependency: int = Field(ge=0, le=10)
    institutional_policy: Literal['Actively_Encouraged','Allowed_With_Citation','Strict_Ban']
    anxiety_level_during_exams: int = Field(ge=0, le=10)


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra='forbid', json_schema_extra={
        'examples': [
            {'student_id': 100001},
            {'features': {
                'major_category':'Humanities','year_of_study':'Senior',
                'pre_semester_gpa':2.418,'weekly_genai_hours':23.31,
                'primary_use_case':'Copywriting/Drafting','prompt_engineering_skill':'Beginner',
                'tool_diversity':1,'paid_subscription':True,'traditional_study_hours':8.13,
                'perceived_ai_dependency':5,'institutional_policy':'Allowed_With_Citation',
                'anxiety_level_during_exams':6,
            }},
        ]
    })
    student_id: int | None = Field(default=None, ge=1, description='ID студента з SQLite')
    features: StudentFeatures | None = Field(default=None, description='Ознаки для нового студента')

    @model_validator(mode='after')
    def exactly_one_input(self):
        if (self.student_id is None) == (self.features is None):
            raise ValueError('Вкажіть або student_id, або features (не обидва)')
        return self


class PredictResponse(BaseModel):
    prediction_id: int
    run_id: str
    source: Literal['inference']
    student_id: int | None
    prediction: Literal['Low','Medium','High']
    probabilities: dict[str, float]
    message: str
