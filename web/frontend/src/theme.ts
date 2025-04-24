import { extendTheme } from '@chakra-ui/react'

const theme = extendTheme({
  config: {
    initialColorMode: 'light',
    useSystemColorMode: false,
  },
  colors: {
    brand: {
      50: '#f5f5f5',
      100: '#e9e9e9',
      200: '#d9d9d9',
      300: '#c4c4c4',
      400: '#9d9d9d',
      500: '#7b7b7b',
      600: '#555555',
      700: '#434343',
      800: '#262626',
      900: '#171717',
    },
    accent: {
      50: '#e6f6ff',
      100: '#b3e3ff',
      200: '#80cfff',
      300: '#4dbbff',
      400: '#1aa7ff',
      500: '#0090e6',
      600: '#006fb3',
      700: '#004d80',
      800: '#002b4d',
      900: '#00121f',
    }
  },
  fonts: {
    heading: "'Inter', sans-serif",
    body: "'Inter', system-ui, sans-serif",
  },
  components: {
    Button: {
      baseStyle: {
        fontWeight: 'semibold',
        borderRadius: 'lg',
        transition: 'all 0.15s ease-in-out',
      },
      variants: {
        solid: {
          bg: 'accent.500',
          color: 'white',
          _hover: {
            bg: 'accent.600',
            transform: 'translateY(-1px)',
          },
          _active: {
            bg: 'brand.600',
            transform: 'translateY(0)',
          },
        },
        outline: {
          borderColor: 'accent.500',
          color: 'accent.500',
          _hover: {
            bg: 'accent.50',
            borderColor: 'accent.600',
            color: 'accent.600',
            transform: 'translateY(-1px)',
          },
          _active: {
            bg: 'brand.50',
            borderColor: 'brand.600',
            color: 'brand.600',
            transform: 'translateY(0)',
          },
        },
        ghost: {
          color: 'accent.500',
          _hover: {
            bg: 'accent.50',
            color: 'accent.600',
            transform: 'translateY(-1px)',
          },
          _active: {
            bg: 'brand.50',
            color: 'brand.600',
            transform: 'translateY(0)',
          },
        },
      },
    },
    Card: {
      baseStyle: {
        container: {
          borderRadius: 'xl',
          boxShadow: 'lg',
          bg: 'white',
          overflow: 'hidden',
          transition: 'all 0.15s ease-in-out',
          _hover: {
            boxShadow: 'xl',
            transform: 'translateY(-2px)',
          },
        },
      },
    },
    Heading: {
      baseStyle: {
        fontWeight: 'bold',
        letterSpacing: '-0.02em',
      },
    },
  },
  styles: {
    global: {
      body: {
        bg: 'gray.50',
        color: 'gray.800',
      },
    },
  },
  layerStyles: {
    card: {
      bg: 'white',
      borderRadius: 'xl',
      boxShadow: 'lg',
      p: 6,
    },
    selected: {
      bg: 'accent.50',
      borderColor: 'accent.500',
      borderWidth: '2px',
    },
  },
  textStyles: {
    h1: {
      fontSize: ['4xl', '5xl'],
      fontWeight: 'bold',
      lineHeight: '110%',
      letterSpacing: '-0.02em',
    },
    h2: {
      fontSize: ['3xl', '4xl'],
      fontWeight: 'semibold',
      lineHeight: '110%',
      letterSpacing: '-0.02em',
    },
  },
})

export default theme 