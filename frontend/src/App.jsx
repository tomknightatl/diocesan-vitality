import { useState, useEffect } from 'react';
import { Container, Table, Spinner, Alert, Navbar, Pagination, Form } from 'react-bootstrap';
import './App.css';

function App() {
  const [dioceses, setDioceses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [summary, setSummary] = useState(null);
  const [summaryLoading, setSummaryLoading] = useState(true);
  const [summaryError, setSummaryError] = useState(null);

  // State for pagination and sorting
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage] = useState(20); // Fixed items per page
  const [totalDioceses, setTotalDioceses] = useState(0);
  const [sortBy, setSortBy] = useState('Name');
  const [sortOrder, setSortOrder] = useState('asc'); // 'asc' or 'desc'

  // State for per-column filtering
  const [filterName, setFilterName] = useState('');
  const [filterAddress, setFilterAddress] = useState('');
  const [filterWebsite, setFilterWebsite] = useState('');

    useEffect(() => {
    const fetchDioceses = async () => {
      setLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams({
          page: currentPage,
          page_size: itemsPerPage,
          sort_by: sortBy,
          sort_order: sortOrder,
        });

        if (filterName) params.append('filter_name', filterName);
        if (filterAddress) params.append('filter_address', filterAddress);
        if (filterWebsite) params.append('filter_website', filterWebsite);

        const response = await fetch(`/api/dioceses?${params.toString()}`);
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        const result = await response.json();
        if (result.error) {
          throw new Error(result.error);
        }
        setDioceses(result.data);
        setTotalDioceses(result.total_count);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDioceses();

    // Fetch summary data (this part remains the same, but moved outside the async function)
    fetch('/api/summary')
      .then(response => {
        if (!response.ok) {
          throw new Error('Network response was not ok');
        }
        return response.json();
      })
      .then(data => {
        if (data.error) {
          throw new Error(data.error);
        }
        setSummary(data);
        setSummaryLoading(false);
      })
      .catch(error => {
        setSummaryError(error.message);
        setSummaryLoading(false);
      });
  }, [currentPage, sortBy, sortOrder, filterName, filterAddress, filterWebsite]); // Dependencies for re-fetching dioceses data

  // Function to handle sorting
  const handleSort = (column) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
    } else {
      setSortBy(column);
      setSortOrder('asc');
    }
  };

  // Calculate total pages for pagination
  const totalPages = Math.ceil(totalDioceses / itemsPerPage);

  // Generate pagination items
  let paginationItems = [];
  for (let number = 1; number <= totalPages; number++) {
    paginationItems.push(
      <Pagination.Item key={number} active={number === currentPage} onClick={() => setCurrentPage(number)}>
        {number}
      </Pagination.Item>,
    );
  }

  return (
    <>
      <Navbar bg="dark" variant="dark">
        <Container>
          <Navbar.Brand href="#home">USCCB Diocese Vitality Index</Navbar.Brand>
        </Container>
      </Navbar>
      <Container className="mt-4">
        <h2>Data Summary</h2>
        {summaryLoading && <Spinner animation="border" />}
        {summaryError && <Alert variant="danger">Error fetching summary: {summaryError}</Alert>}
        {!summaryLoading && !summaryError && summary && (
          <Table striped bordered hover responsive className="mb-4">
            <thead>
              <tr>
                <th>Total Dioceses Processed</th>
                <th>Parish Directories Found</th>
                <th>Parish Directories Not Found</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{summary.total_dioceses_processed}</td>
                <td>{summary.found_parish_directories}</td>
                <td>{summary.not_found_parish_directories}</td>
              </tr>
            </tbody>
          </Table>
        )}

        <h2>Dioceses Data</h2>
        <p>Displaying the first 20 records from the database.</p>
        {loading && <Spinner animation="border" />}
        {error && <Alert variant="danger">Error fetching data: {error}</Alert>}
        {!loading && !error && (
          <Table striped bordered hover responsive>
            <thead>
              <tr>
                <th style={{ cursor: 'pointer' }}>
                  <div onClick={() => handleSort('Name')}>
                    Name {sortBy === 'Name' && (sortOrder === 'asc' ? '▲' : '▼')}
                  </div>
                  <Form.Control
                    type="text"
                    placeholder="Filter Name"
                    value={filterName}
                    onChange={(e) => setFilterName(e.target.value)}
                    onClick={(e) => e.stopPropagation()} // Prevent sorting when clicking input
                    className="mt-1"
                  />
                </th>
                <th style={{ cursor: 'pointer' }}>
                  <div onClick={() => handleSort('Address')}>
                    Address {sortBy === 'Address' && (sortOrder === 'asc' ? '▲' : '▼')}
                  </div>
                  <Form.Control
                    type="text"
                    placeholder="Filter Address"
                    value={filterAddress}
                    onChange={(e) => setFilterAddress(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className="mt-1"
                  />
                </th>
                <th style={{ cursor: 'pointer' }}>
                  <div onClick={() => handleSort('Website')}>
                    Website {sortBy === 'Website' && (sortOrder === 'asc' ? '▲' : '▼')}
                  </div>
                  <Form.Control
                    type="text"
                    placeholder="Filter Website"
                    value={filterWebsite}
                    onChange={(e) => setFilterWebsite(e.target.value)}
                    onClick={(e) => e.stopPropagation()}
                    className="mt-1"
                  />
                </th>
              </tr>
            </thead>
            <tbody>
              {dioceses.map((diocese, index) => (
                <tr key={diocese.id || index}>
                  <td>{diocese.Name}</td>
                  <td>{diocese.Address}</td>
                  <td><a href={diocese.Website} target="_blank" rel="noopener noreferrer">{diocese.Website}</a></td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}

        {/* Pagination Controls */}
        {!loading && !error && totalPages > 1 && (
          <div className="d-flex justify-content-center mt-3">
            <Pagination>
              <Pagination.Prev onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))} disabled={currentPage === 1} />
              {paginationItems}
              <Pagination.Next onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))} disabled={currentPage === totalPages} />
            </Pagination>
          </div>
        )}
      </Container>

      <Container className="mt-4">
        <h2>Reports</h2>
        <div className="row">
          {/* Dioceses Charts (Left Side) */}
          <div className="col-md-6">
            <div className="p-2">
              <h3>Dioceses Records Over Time</h3>
              <img src="/dioceses_records_over_time.png" alt="Dioceses Records Over Time" className="img-fluid mb-3" />
            </div>
            <div className="p-2">
              <h3>Dioceses Parish Directory Records Over Time</h3>
              <img src="/diocesesparishdirectory_records_over_time.png" alt="Dioceses Parish Directory Records Over Time" className="img-fluid mb-3" />
            </div>
          </div>
          {/* Parishes Charts (Right Side) */}
          <div className="col-md-6">
            <div className="p-2">
              <h3>Parishes Records Over Time</h3>
              <img src="/parishes_records_over_time.png" alt="Parishes Records Over Time" className="img-fluid mb-3" />
            </div>
            <div className="p-2">
              <h3>Parish Schedules Records Over Time</h3>
              <img src="/parishschedules_records_over_time.png" alt="Parish Schedules Records Over Time" className="img-fluid mb-3" />
            </div>
          </div>
        </div>
      </Container>
    </>
  );
}

export default App;