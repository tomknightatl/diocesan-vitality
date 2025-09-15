import React, { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { Container, Spinner, Alert, Card } from 'react-bootstrap';

function Parish() {
  const { search } = useLocation();
  const queryParams = new URLSearchParams(search);
  const id = queryParams.get('id');

  const [parish, setParish] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchParishDetails = async () => {
      if (!id) {
        setError('Parish ID not provided.');
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`/api/parish?parish_id=${id}`);
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        const result = await response.json();
        if (result.error) {
          throw new Error(result.error);
        }
        setParish(result.data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchParishDetails();
  }, [id]);

  if (loading) {
    return <Spinner animation="border" />;
  }

  if (error) {
    return <Alert variant="danger">Error fetching parish details: {error}</Alert>;
  }

  if (!parish) {
    return <Alert variant="info">No parish data found.</Alert>;
  }

  return (
    <Container className="mt-4">
      <Card>
        <Card.Header as="h2">{parish.Name}</Card.Header>
        <Card.Body>
          <Card.Text>
            <strong>Address:</strong> {parish.Address}
          </Card.Text>
          <Card.Text>
            <strong>Website:</strong> <a href={parish.Website} target="_blank" rel="noopener noreferrer">{parish.Website}</a>
          </Card.Text>
          {/* Add more parish details here */}
          <h3>Schedules</h3>
          {/* Display schedules here */}
          <p>Schedules for {parish.Name} will be displayed here.</p>
        </Card.Body>
      </Card>
    </Container>
  );
}

export default Parish;