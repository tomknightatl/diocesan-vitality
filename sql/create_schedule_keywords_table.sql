-- Create the ScheduleKeywords table for managing extraction keywords
CREATE TABLE IF NOT EXISTS public."ScheduleKeywords" (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at timestamptz DEFAULT now(),
    updated_at timestamptz DEFAULT now(),
    
    -- Keyword information
    keyword text NOT NULL,
    schedule_type text NOT NULL CHECK (schedule_type IN ('reconciliation', 'adoration', 'both')),
    weight integer NOT NULL DEFAULT 1,
    is_negative boolean DEFAULT false,
    
    -- Configuration and metadata
    is_active boolean DEFAULT true,
    description text,
    examples text,
    
    -- Unique constraint to prevent duplicate keywords for the same type
    UNIQUE(keyword, schedule_type)
);

-- Enable Row Level Security
ALTER TABLE public."ScheduleKeywords" ENABLE ROW LEVEL SECURITY;

-- Create RLS policy (allow read/write for authenticated users)
CREATE POLICY "Enable all operations for authenticated users" 
ON public."ScheduleKeywords"
FOR ALL 
TO authenticated
USING (true)
WITH CHECK (true);

-- Create RLS policy for anonymous read access (if needed)
CREATE POLICY "Enable read access for anonymous users" 
ON public."ScheduleKeywords"
FOR SELECT 
TO anon
USING (true);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_schedule_keywords_type ON public."ScheduleKeywords"(schedule_type);
CREATE INDEX IF NOT EXISTS idx_schedule_keywords_active ON public."ScheduleKeywords"(is_active);
CREATE INDEX IF NOT EXISTS idx_schedule_keywords_weight ON public."ScheduleKeywords"(weight DESC);

-- Insert existing reconciliation keywords (positive)
INSERT INTO public."ScheduleKeywords" (keyword, schedule_type, weight, is_negative, description) VALUES
('reconciliation', 'reconciliation', 5, false, 'Primary reconciliation keyword'),
('confession', 'reconciliation', 5, false, 'Alternative term for reconciliation'),
('schedule', 'reconciliation', 8, false, 'High-weight schedule indicator'),
('times', 'reconciliation', 3, false, 'Schedule timing indicator'),
('sacrament', 'reconciliation', 1, false, 'General sacramental reference');

-- Insert existing reconciliation keywords (negative)
INSERT INTO public."ScheduleKeywords" (keyword, schedule_type, weight, is_negative, description) VALUES
('adoration', 'reconciliation', 2, true, 'Negative keyword - indicates different sacrament'),
('baptism', 'reconciliation', 2, true, 'Negative keyword - indicates different sacrament'),
('donate', 'reconciliation', 2, true, 'Negative keyword - indicates non-sacramental content'),
('giving', 'reconciliation', 2, true, 'Negative keyword - indicates non-sacramental content');

-- Insert existing adoration keywords (positive)
INSERT INTO public."ScheduleKeywords" (keyword, schedule_type, weight, is_negative, description) VALUES
('adoration', 'adoration', 5, false, 'Primary adoration keyword'),
('eucharist', 'adoration', 5, false, 'Alternative term for eucharistic adoration'),
('schedule', 'adoration', 3, false, 'Schedule indicator for adoration'),
('times', 'adoration', 3, false, 'Schedule timing indicator'),
('perpetual', 'adoration', 4, false, 'Perpetual adoration indicator'),
('exposition', 'adoration', 4, false, 'Eucharistic exposition term'),
('blessed sacrament', 'adoration', 5, false, 'Traditional term for eucharistic adoration');

-- Insert existing adoration keywords (negative)
INSERT INTO public."ScheduleKeywords" (keyword, schedule_type, weight, is_negative, description) VALUES
('reconciliation', 'adoration', 2, true, 'Negative keyword - indicates different sacrament'),
('confession', 'adoration', 2, true, 'Negative keyword - indicates different sacrament'),
('baptism', 'adoration', 2, true, 'Negative keyword - indicates different sacrament'),
('donate', 'adoration', 2, true, 'Negative keyword - indicates non-sacramental content'),
('giving', 'adoration', 2, true, 'Negative keyword - indicates non-sacramental content');

-- Insert some additional useful keywords
INSERT INTO public."ScheduleKeywords" (keyword, schedule_type, weight, is_negative, description) VALUES
('holy hour', 'adoration', 4, false, 'Common adoration term'),
('chapel', 'both', 2, false, 'Location indicator for both types'),
('hours', 'both', 3, false, 'Schedule timing indicator'),
('daily', 'both', 2, false, 'Frequency indicator'),
('weekly', 'both', 2, false, 'Frequency indicator'),
('penance', 'reconciliation', 3, false, 'Alternative reconciliation term'),
('confessional', 'reconciliation', 4, false, 'Reconciliation location indicator'),
('confessionals', 'reconciliation', 4, false, 'Reconciliation location indicator (plural)'),
('by appointment', 'both', 3, false, 'Scheduling availability indicator');

-- Add a trigger to automatically update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_schedule_keywords_updated_at 
    BEFORE UPDATE ON public."ScheduleKeywords" 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create a view for easy querying of active keywords by type
CREATE OR REPLACE VIEW public."ActiveScheduleKeywords" AS
SELECT 
    id,
    keyword,
    schedule_type,
    weight,
    is_negative,
    description,
    created_at,
    updated_at
FROM public."ScheduleKeywords"
WHERE is_active = true
ORDER BY schedule_type, weight DESC, keyword;

-- Display the populated table
SELECT 
    schedule_type,
    keyword,
    weight,
    is_negative,
    description
FROM public."ScheduleKeywords"
ORDER BY schedule_type, is_negative, weight DESC;