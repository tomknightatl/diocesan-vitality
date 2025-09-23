import { Link, Outlet, useLocation } from 'react-router-dom';
import { Container, Navbar, Nav } from 'react-bootstrap';

function Layout() {
  const location = useLocation();

  return (
    <>
      <Navbar bg="dark" variant="dark">
        <Container>
          <Nav className="me-auto">
            <Nav.Link
              as={Link}
              to="/"
              style={{
                color: location.pathname === '/' ? 'white' : '',
                fontSize: '1.4rem',
                border: '1px solid #495057',
                borderRadius: '4px',
                marginRight: '8px',
                padding: '8px 16px'
              }}
            >
              Dioceses
            </Nav.Link>
            <Nav.Link
              as={Link}
              to="/parishes"
              style={{
                color: location.pathname === '/parishes' ? 'white' : '',
                fontSize: '1.4rem',
                border: '1px solid #495057',
                borderRadius: '4px',
                marginRight: '8px',
                padding: '8px 16px'
              }}
            >
              Parishes
            </Nav.Link>
            <Nav.Link
              as={Link}
              to="/reports"
              style={{
                color: location.pathname === '/reports' ? 'white' : '',
                fontSize: '1.4rem',
                border: '1px solid #495057',
                borderRadius: '4px',
                marginRight: '8px',
                padding: '8px 16px'
              }}
            >
              History
            </Nav.Link>
            <Nav.Link
              as={Link}
              to="/dashboard"
              style={{
                color: location.pathname === '/dashboard' ? 'white' : '',
                fontSize: '1.4rem',
                border: '1px solid #495057',
                borderRadius: '4px',
                marginRight: '8px',
                padding: '8px 16px'
              }}
            >
              Health
            </Nav.Link>
          </Nav>
          <Navbar.Brand href="/" style={{ fontSize: '1.6rem' }}>Diocesan Vitality</Navbar.Brand>
        </Container>
      </Navbar>
      <Outlet />
    </>
  );
}

export default Layout;
