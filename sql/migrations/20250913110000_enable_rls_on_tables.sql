-- Enable Row Level Security for the specified tables

ALTER TABLE public.test_parishes_expected_2009 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.expected_parishes_2002 ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."ParishData" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public."DiscoveredUrls" ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.parishfactssuppressionurls ENABLE ROW LEVEL SECURITY;
