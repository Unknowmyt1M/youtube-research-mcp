export interface CodeTab {
  language: string;
  label: string;
  code: string;
  filename?: string;
}

export interface ParamDef {
  name: string;
  type: string;
  required: boolean;
  default?: string;
  description: string;
}

export interface CalloutDef {
  type: 'note' | 'tip' | 'important' | 'warning';
  title?: string;
  content: string;
}

export interface DocSection {
  id: string;
  title: string;
  content?: string;
  callouts?: CalloutDef[];
  codeTabs?: CodeTab[];
  params?: ParamDef[];
  returns?: string;
  subsections?: {
    id: string;
    title: string;
    content: string;
    codeTabs?: CodeTab[];
  }[];
}

export interface DocPage {
  id: string;
  title: string;
  category: string;
  description: string;
  badge?: string;
  updatedAt?: string;
  sections: DocSection[];
  relatedPages?: { id: string; title: string; category: string }[];
}

export interface DocCategory {
  id: string;
  title: string;
  icon: string;
  pages: DocPage[];
}
