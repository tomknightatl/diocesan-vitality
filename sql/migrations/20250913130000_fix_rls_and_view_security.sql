-- Enable Row Level Security for the ParishData table
ALTER TABLE public."ParishData" ENABLE ROW LEVEL SECURITY;

-- Alter the view ParishScheduleSummary to use SECURITY INVOKER
ALTER VIEW public."ParishScheduleSummary" SET (security_invoker = true);
