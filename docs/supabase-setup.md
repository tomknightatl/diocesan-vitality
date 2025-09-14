# Supabase Table Setup and Row Level Security (RLS)

This document provides general instructions for setting up new tables in Supabase and configuring Row Level Security (RLS) policies.

## 1. Create the Table

You can create your table using the Supabase SQL Editor or by defining it in your database migration files.

**Example SQL for creating a new table (replace with your table name and columns):**

```sql
CREATE TABLE public."YourTableName" (
    id uuid PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at timestamptz DEFAULT now(),
    -- Add your specific columns here
    name text,
    description text
);
```

## 2. Enable Row Level Security (RLS)

After creating the table, you **must** enable RLS to control access to its rows. This is a crucial step for securing your data.

```sql
ALTER TABLE public."YourTableName" ENABLE ROW LEVEL SECURITY;
```

## 3. Create RLS Policies

After enabling RLS for your table (as described in Section 2), you need to create policies that define who can access which rows and under what conditions. You'll typically create policies for `SELECT`, `INSERT`, `UPDATE`, and `DELETE` operations.

**Example Policy for Public Access (similar to "Allow notebook access"):**

If you want to allow public (unauthenticated) access for all operations, similar to how some Supabase tables are configured for quick setup or specific use cases, you can use a single policy like this:

```sql
CREATE POLICY "Allow public access to YourTableName"
ON public."YourTableName" FOR ALL
TO public
USING (true) WITH CHECK (true);
```

**Common Policies for Authenticated Users (adjust as needed):**

If you prefer to restrict access to authenticated users, or have more granular control, you would create separate policies for each operation:

*   **Policy for SELECT (Read Access):**
    Allows authenticated users to read all rows.
    ```sql
    CREATE POLICY "Allow authenticated users to view YourTableName"
    ON public."YourTableName" FOR SELECT
    TO authenticated
    USING (true);
    ```

*   **Policy for INSERT (Write Access):**
    Allows authenticated users to insert new rows.
    ```sql
    CREATE POLICY "Allow authenticated users to insert YourTableName"
    ON public."YourTableName" FOR INSERT
    TO authenticated
    WITH CHECK (true);
    ```

*   **Policy for UPDATE (Modify Access):**
    Allows authenticated users to update existing rows.
    ```sql
    CREATE POLICY "Allow authenticated users to update YourTableName"
    ON public."YourTableName" FOR UPDATE
    TO authenticated
    USING (true) WITH CHECK (true);
    ```

*   **Policy for DELETE (Remove Access):**
    Allows authenticated users to delete rows.
    ```sql
    CREATE POLICY "Allow authenticated users to delete YourTableName"
    ON public."YourTableName" FOR DELETE
    TO authenticated
    USING (true);
    ```

**Important Considerations:**

*   **`USING (true)`**: This means the policy applies to all rows. For more granular control (e.g., users can only see their own data), you would replace `true` with a condition like `auth.uid() = user_id`.
*   **`WITH CHECK (true)`**: This applies to `INSERT` and `UPDATE` operations, ensuring that the new or updated row also satisfies the condition.
*   **`TO authenticated`**: This grants permission to users who are authenticated. You can change this to `public` for unauthenticated access, or specific roles.
*   **Primary Key for `upsert`**: If you are using `upsert` in your application code, ensure your table has a primary key defined, and that your `upsert` call specifies the `on_conflict` column(s).

Remember to replace `"YourTableName"` with the actual name of your table.
